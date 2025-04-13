from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    # Extends User model with additional profile information
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # Automatically creates a Profile when a new User is created
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Saves the Profile whenever the associated User is saved
    instance.profile.save()