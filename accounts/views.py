from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import logout
from .models import Profile
from media_app.models import MediaProject
from django.db.models import Q
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

# Configure logging for this module
logger = logging.getLogger(__name__)


def register(request):
    # Handles user registration and account creation
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    # Handles profile display, updates, project listing, and project deletion
    # Ensure user has a profile, creating one if needed
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Get search query parameter if provided
    search_query = request.GET.get('search', '')

    # Get user's projects
    projects = MediaProject.objects.filter(user=request.user)

    # Filter projects by search query if provided
    if search_query:
        projects = projects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Sort projects by creation date (newest first)
    projects = projects.order_by('-created_at')

    if request.method == 'POST':
        # Handle project deletion
        if 'delete_project' in request.POST:
            project_id = request.POST.get('project_id')
            try:
                project = MediaProject.objects.get(id=project_id, user=request.user)
                project.delete()
                messages.success(request, f'Project "{project.title}" deleted successfully!')
            except MediaProject.DoesNotExist:
                messages.error(request, 'Project not found or you do not have permission.')
            except Exception as e:
                logger.error(f"Error deleting project {project_id}: {str(e)}")
                messages.error(request, f'An error occurred: {str(e)}')
            return redirect('profile')

        # Handle profile update
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        # Initialize forms with current user data
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    # Prepare template context
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'projects': projects,
        'search_query': search_query
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def logout_view(request):
    # Handles user logout and redirects to login page
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')