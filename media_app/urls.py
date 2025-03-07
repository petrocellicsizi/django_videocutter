# media_app/urls.py
from django.urls import path
from . import views
from .views import update_project_type
urlpatterns = [
    path('', views.home, name='home'),
    path('projects/new/', views.create_project, name='create_project'),
    path('project/<int:pk>/update-type/', update_project_type, name='update_project_type'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/process/', views.process_project, name='process_project'),
    path('items/reorder/', views.update_item_order, name='update_item_order'),
    path('items/<int:item_id>/delete/', views.delete_item, name='delete_item'),
]