from django.shortcuts import render
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Profile
from media_app.models import MediaProject


def register(request):
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

# accounts/views.py (or wherever your profile view is)
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UserUpdateForm, ProfileUpdateForm  # Adjust import as needed
from media_app.models import MediaProject  # Adjust import based on your app structure

logger = logging.getLogger(__name__)


@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    projects = MediaProject.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
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

        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'projects': projects
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')  # Redirect to the login page
