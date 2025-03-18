# media_app/views.py
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
    return render(request, 'media_app/home.html')


@login_required
def update_project_type(request, pk):
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
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)
    items = project.media_items.all().order_by('order')

    if request.method == 'POST':
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media_item = form.save(commit=False)
            media_item.project = project
            media_item.order = items.count()
            media_item.save()
            messages.success(request, 'Media added successfully!')
            return redirect('project_detail', pk=project.pk)
        else:
            # Form is not valid, but don't redirect away from the project
            # Just show error messages
            for error in form.errors.get('file', []):
                messages.error(request, error)
            # Return to the same page with the filled form
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
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    if project.media_items.count() == 0:
        messages.error(request, 'Add media to your project before processing!')
        return redirect('project_detail', pk=project.pk)

    # First update the status to let the user know processing has started
    project.status = 'processing'
    project.save()

    # Start processing in background thread
    thread = threading.Thread(target=process_media_project, args=(project,))
    thread.daemon = True  # Make sure thread doesn't block server shutdown
    thread.start()

    messages.info(request,'Project processing started. This may take some time.')
    return redirect('project_detail', pk=project.pk)


@login_required
@require_POST
def update_item_order(request):
    item_ids = request.POST.getlist('item_order[]')

    for index, item_id in enumerate(item_ids):
        item = get_object_or_404(MediaItem, id=item_id)
        # Ensure user can only reorder their own items
        if item.project.user != request.user:
            return JsonResponse({'status': 'error'}, status=403)

        item.order = index
        item.save()

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_item(request, item_id):
    item = get_object_or_404(MediaItem, id=item_id)

    # Ensure user can only delete their own items
    if item.project.user != request.user:
        messages.error(request, 'You do not have permission to delete this item.')
        return redirect('project_detail', pk=item.project.pk)

    project_id = item.project.id
    item.delete()

    messages.success(request, 'Media item deleted successfully.')
    return redirect('project_detail', pk=project_id)


@login_required
def check_project_status(request, pk):
    """AJAX endpoint to check the processing status of a project"""
    project = get_object_or_404(MediaProject, pk=pk, user=request.user)

    data = {
        'status': project.status,
    }

    # If completed, include the output file URL
    if project.status == 'completed' and project.output_file:
        data['output_file'] = project.output_file.url
        # Add success message
        data['success_message'] = 'Project processing finished!'

        # Update QR code with actual URL if not already updated
        if project.qr_code and "PLACEHOLDER_URL" in generate_actual_qr_code(request, project):
            # Full URL to the video
            video_url = request.build_absolute_uri(project.output_file.url)
            update_qr_code(project, video_url)

        if project.qr_code:
            data['qr_code'] = project.qr_code.url
    return JsonResponse(data)


def generate_actual_qr_code(request, project):
    """Check if QR code needs to be updated with actual URL"""
    try:
        if not project.qr_code:
            return "No QR code available"

        qr_path = os.path.join(settings.MEDIA_ROOT, project.qr_code.name)

        # Check if the QR code exists
        if not os.path.exists(qr_path):
            return "QR code file not found"

        # For debugging - return placeholder to indicate it needs updating
        return "PLACEHOLDER_URL"

    except Exception as e:
        print(f"Error checking QR code: {str(e)}")
        return "Error checking QR code"


def update_qr_code(project, video_url):
    """Update the QR code with the actual video URL"""
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
