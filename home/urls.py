from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('events/<int:event_id>/apply/<int:talent_id>/', views.apply_for_event, name='apply_for_event'),
    path('events/<int:event_id>/withdraw/<int:talent_id>/', views.withdraw_application, name='withdraw_application'),
    path('events/<int:event_id>/application/<int:application_id>/<str:new_status>/', views.update_application_status, name='update_application_status'),
    path('debug/user/', views.debug_user, name='debug_user'),
    path('events/json/', views.events_json, name='events_json'),
    path('events/json/<str:username>/', views.events_json, name='events_json_user'),
    path('calendar/', views.event_list, name='calendar'),
    path('calendar/<str:username>/', views.event_list, name='user_calendar'),
    path('availability/json/', views.availability_json, name='availability_json'),
    path('availability/json/<str:username>/', views.availability_json, name='availability_json_user'),
    path('availability/create/', views.create_availability, name='create_availability'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
