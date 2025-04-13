from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MediaProject, MediaItem
from .forms import MediaProjectForm, MediaItemForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import threading
from .media_processor import process_media_project
import qrcode
import os
from django.conf import settings


@login_required
def home(request):
    # Renders the home page for authenticated users only
    return render(request, 'media_app/home.html')


@login_required
def update_project_type(request, pk):
    # Updates the project type for an existing project
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    if request.method == 'POST':
        new_type = request.POST.get('type')
        if new_type in dict(MediaProject.PROJECT_TYPES):  # Ensure valid choice
            project.type = new_type
            project.save()
            messages.success(request, 'Project type updated successfully!')

    return redirect('project_detail', pk=pk)


@login_required
def update_project_details(request, pk):
    # Updates title and description for an existing project
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        if title:  # Title is required
            project.title = title
            project.description = description
            project.save()
            messages.success(request, 'Project details updated successfully!')
        else:
            messages.error(request, 'Project title cannot be empty.')

    return redirect('project_detail', pk=pk)


@login_required
def create_project(request):
    # Handles creation of new media projects
    project_type = request.GET.get('type')

    if request.method == 'POST':
        form = MediaProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, 'Project created successfully!')
            return redirect('project_detail', pk=project.pk)
        else:
            # Show form errors but don't redirect
            pass
    else:
        if project_type in dict(MediaProject.PROJECT_TYPES):
            form = MediaProjectForm(initial={'type': project_type})
        else:
            form = MediaProjectForm()

    return render(request, 'media_app/create_project.html', {'form': form})


@login_required
def project_detail(request, pk):
    # Displays project details and handles adding new media items
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)
    items = project.media_items.all().order_by('order')

    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media_item = form.save(commit=False)
            media_item.project = project
            media_item.order = items.count()  # Add at the end of the list
            media_item.save()
            messages.success(request, 'Media added successfully!')
            return redirect('project_detail', pk=project.pk)
        else:
            # Form is not valid, show error messages
            for error in form.errors.get('file', []):
                messages.error(request, error)
    else:
        form = MediaItemForm()

    return render(request, 'media_app/create_project.html', {
        'project': project,
        'items': items,
        'form': form
    })


@login_required
@require_POST
def process_project(request, pk):
    # Initiates background processing of media project
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    if project.media_items.count() == 0:
        messages.error(request, 'Add media to your project before processing!')
        return redirect('project_detail', pk=project.pk)

    # Update status to show processing has started
    project.status = 'processing'
    project.save()

    # Start processing in background thread
    thread = threading.Thread(target=process_media_project, args=(project,))
    thread.daemon = True  # Ensure thread doesn't block server shutdown
    thread.start()

    messages.info(request,'Project processing started. This may take some time.')
    return redirect('project_detail', pk=project.pk)


@login_required
@require_POST
def update_item_order(request):
    # Updates the order of media items in a project via AJAX
    item_ids = request.POST.getlist('item_order[]')

    for index, item_id in enumerate(item_ids):
        item = get_object_or_404(MediaItem, id=item_id)
        # Security check: ensure user owns the items
        if item.project.user != request.user:
            return JsonResponse({'status': 'error'}, status=403)

        item.order = index
        item.save()

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_item(request, item_id):
    # Deletes a media item from a project
    item = get_object_or_404(MediaItem, id=item_id)
    project = item.project

    # Security check: ensure user owns the item
    if project.user != request.user:
        messages.error(request, 'You do not have permission to delete this item.')
        return redirect('project_detail', pk=project.pk)

    # Prevent deletion during processing
    if project.status == 'processing':
        messages.error(request,
                       'Cannot delete media while the project is being processed. Please wait for processing to complete.')
        return redirect('project_detail', pk=project.pk)

    try:
        item.delete()
        messages.success(request, 'Media item deleted successfully.')
    except PermissionError:
        messages.error(request, 'Cannot delete media. The file may be in use by another process. Try again later.')

    return redirect('project_detail', pk=project.pk)


@login_required
def check_project_status(request, pk):
    # AJAX endpoint to check project processing status
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    data = {
        'status': project.status,
    }

    # For completed projects, include output file information
    if project.status == 'completed':
        # Prioritize Google Drive link if available
        if project.drive_web_view_link:
            data['drive_web_view_link'] = project.drive_web_view_link
            data['output_file'] = project.drive_web_view_link  # For backward compatibility
            data['is_drive_link'] = True
        elif project.output_file:
            data['output_file'] = project.output_file.url
            data['is_drive_link'] = False

        # Add success message
        data['success_message'] = 'Project processing finished!'

        # Include QR code if available
        if project.qr_code:
            data['qr_code'] = project.qr_code.url

        # Update QR code if needed (for local storage)
        if not project.drive_web_view_link and project.qr_code and "PLACEHOLDER_URL" in generate_actual_qr_code(request,
                                                                                                                project):
            # Full URL to the video
            video_url = request.build_absolute_uri(project.output_file.url)
            update_qr_code(project, video_url)
            if project.qr_code:
                data['qr_code'] = project.qr_code.url

    return JsonResponse(data)


def generate_actual_qr_code(request, project):
    # Checks if QR code exists and needs updating
    try:
        if not project.qr_code:
            return "No QR code available"

        qr_path = os.path.join(settings.MEDIA_ROOT, project.qr_code.name)

        # Check if the QR code exists
        if not os.path.exists(qr_path):
            return "QR code file not found"

        # Return placeholder to indicate it needs updating
        return "PLACEHOLDER_URL"

    except Exception as e:
        print(f"Error checking QR code: {str(e)}")
        return "Error checking QR code"


def update_qr_code(project, video_url):
    # Updates QR code to link to the actual video URL
    try:
        qr_path = os.path.join(settings.MEDIA_ROOT, project.qr_code.name)

        # Create QR code object
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Add the actual video URL
        qr.add_data(video_url)
        qr.make(fit=True)

        # Create and save the QR code image
        img = qr.make_image(fill="black", back_color="white")
        img.save(qr_path)

        return True
    except Exception as e:
        print(f"Error updating QR code: {str(e)}")
        return False