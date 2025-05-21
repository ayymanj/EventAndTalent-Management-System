from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/edit/', views.update_profile, name='update_profile'),
    path('messages/', views.messages_view, name='messages'),
    path('messages/<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('messages/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('messages/start/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('calendar/availability/', views.update_availability, name='update_availability'),
    path('calendar/events/add/', views.add_calendar_event, name='add_calendar_event'),
    path('calendar/events/<int:event_id>/delete/', views.delete_calendar_event, name='delete_calendar_event'),
    path('support/', views.support_view, name='support'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('users/', views.user_list, name='user_list'),
] 