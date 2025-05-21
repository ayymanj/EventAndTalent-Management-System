from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth import login, authenticate
from django.urls import reverse
from .forms import CustomSignupForm
from .models import Profile, Conversation, Message, Notification, CalendarEvent
from home.models import Event, EventApplication, Availability
from django.utils import timezone
from types import SimpleNamespace
from .utils import create_notification

# Create your views here.

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
    else:
        form = CustomSignupForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def dashboard(request):
    # Ensure user has a profile
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    # Get the active tab from the request, defaulting based on user role
    active_tab = request.GET.get('tab')
    if not active_tab:
        if request.user.profile.role == 'organizer':
            active_tab = 'events'
        else:
            active_tab = 'applications'
    
    context = {
        'active_tab': active_tab,
        'user': request.user,
    }
    
    # Handle tab content based on user role
    if request.user.profile.role == 'organizer':
        if active_tab == 'events':
            context['events'] = Event.objects.filter(
                organizer=request.user
            ).order_by('-created_at')
        elif active_tab == 'requests':
            context['requests'] = EventApplication.objects.filter(
                event__organizer=request.user
            ).select_related('performer', 'event').order_by('-created_at')
    else:  # Performer
        if active_tab == 'applications':
            context['applications'] = EventApplication.objects.filter(
                performer=request.user
            ).select_related('event', 'talent_type').order_by('-created_at')
    
    # Handle profile and settings tabs
    if active_tab == 'profile':
        if request.method == 'POST':
            username = request.POST.get('username')
            email = request.POST.get('email')
            bio = request.POST.get('bio')
            
            if username != request.user.username:
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already taken.')
                else:
                    request.user.username = username
            
            if email != request.user.email:
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already taken.')
                else:
                    request.user.email = email
            
            request.user.save()
            request.user.profile.bio = bio
            request.user.profile.save()
            
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard')
    elif active_tab == 'settings':
        if request.method == 'POST':
            email_notifications = request.POST.get('email_notifications') == 'on'
            application_updates = request.POST.get('application_updates') == 'on'
            show_profile = request.POST.get('show_profile') == 'on'
            
            request.user.profile.email_notifications = email_notifications
            request.user.profile.application_updates = application_updates
            request.user.profile.show_profile = show_profile
            request.user.profile.save()
            
            messages.success(request, 'Settings updated successfully.')
            return redirect('dashboard')
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def messages_view(request):
    conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    for conversation in conversations:
        conversation.other_user = conversation.participants.exclude(id=request.user.id).first()
        # Get unread count for each conversation
        conversation.unread_count = Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user).count()
    return render(request, 'accounts/messages.html', {
        'conversations': conversations
    })

@login_required
def conversation_view(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    messages = conversation.messages.all().order_by('created_at')
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    # Mark unread messages as read
    unread_messages = messages.filter(is_read=False).exclude(sender=request.user)
    unread_messages.update(is_read=True)
    
    return render(request, 'accounts/conversation.html', {
        'conversation': conversation,
        'messages': messages,
        'other_user': other_user
    })

@login_required
def send_message(request, conversation_id=None, recipient_id=None):
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if request.user not in conversation.participants.all():
            messages.error(request, 'You do not have permission to send messages in this conversation.')
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    elif recipient_id:
        recipient = get_object_or_404(User, id=recipient_id)
        conversation, created = Conversation.objects.get_or_create_conversation(request.user, recipient)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()
            
            # Create notifications for all participants except the sender
            for participant in conversation.participants.exclude(id=request.user.id):
                create_notification(
                    user=participant,
                    notification_type='message',
                    title='New Message',
                    message=f'You have a new message from {request.user.username}',
                    link=reverse('conversation', args=[conversation.id])
                )
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'created_at': message.created_at.isoformat()
                }
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Message content is required'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def start_conversation(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Check if conversation already exists
    existing_conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_conversation:
        return redirect('conversation', conversation_id=existing_conversation.id)
    
    # Create new conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    
    return redirect('conversation', conversation_id=conversation.id)

@login_required
def notifications_view(request):
    notifications = request.user.notifications.all()
    
    # Mark all notifications as read when the page is viewed
    request.user.notifications.filter(is_read=False).update(is_read=True)
    
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'status': 'success'})
    
    return render(request, 'accounts/notifications.html', {
        'notifications': notifications
    })

@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def update_profile(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        bio = request.POST.get('bio')
        
        if username != request.user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken.')
            else:
                request.user.username = username
        
        if email != request.user.email:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already taken.')
            else:
                request.user.email = email
        
        request.user.save()
        request.user.profile.bio = bio
        request.user.profile.save()
        
        messages.success(request, 'Profile updated successfully.')
    
    return redirect('dashboard')

@login_required
def update_availability(request):
    if request.method == 'POST':
        try:
            # Delete existing availabilities
            Availability.objects.filter(user=request.user).delete()
            
            # Get availability data from request
            days = request.POST.getlist('days[]')
            dates = request.POST.getlist('dates[]')
            start_times = request.POST.getlist('start_times[]')
            end_times = request.POST.getlist('end_times[]')
            is_available = request.POST.getlist('is_available[]')
            is_recurring = request.POST.getlist('is_recurring[]')
            
            # Create new availabilities
            for i in range(len(start_times)):
                if not start_times[i] or not end_times[i]:
                    continue
                    
                if is_recurring[i] == 'true':
                    # Create recurring availability
                    if not days[i]:
                        continue
                    Availability.objects.create(
                        user=request.user,
                        day_of_week=int(days[i]),
                        start_time=start_times[i],
                        end_time=end_times[i],
                        is_available=is_available[i] == 'true',
                        is_recurring=True
                    )
                else:
                    # Create date-based availability
                    if not dates[i]:
                        continue
                    Availability.objects.create(
                        user=request.user,
                        date=dates[i],
                        start_time=start_times[i],
                        end_time=end_times[i],
                        is_available=is_available[i] == 'true',
                        is_recurring=False
                    )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def add_calendar_event(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location = request.POST.get('location')
        
        event = CalendarEvent.objects.create(
            user=request.user,
            title=title,
            description=description,
            event_type=event_type,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location
        )
        
        return JsonResponse({
            'status': 'success',
            'event': {
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'event_type': event.event_type,
                'date': event.date.strftime('%Y-%m-%d'),
                'start_time': event.start_time.strftime('%H:%M'),
                'end_time': event.end_time.strftime('%H:%M'),
                'location': event.location
            }
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_calendar_event(request, event_id):
    try:
        event = CalendarEvent.objects.get(id=event_id, user=request.user)
        event.delete()
        return JsonResponse({'status': 'success'})
    except CalendarEvent.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)

def about_view(request):
    return render(request, 'accounts/about.html')

def support_view(request):
    return render(request, 'accounts/support.html')

def contact_view(request):
    return render(request, 'accounts/contact.html')

def terms_view(request):
    return render(request, 'accounts/terms.html')

def privacy_view(request):
    return render(request, 'accounts/privacy.html')

@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    availabilities = Availability.objects.filter(user=profile_user)
    calendar_events = CalendarEvent.objects.filter(
        user=profile_user,
        date__gte=timezone.now().date()
    )
    upcoming_events = list(calendar_events)
    if hasattr(profile_user, 'profile') and profile_user.profile.role == 'organizer':
        # Add upcoming events organized by this user
        org_events = Event.objects.filter(
            organizer=profile_user,
            date__gte=timezone.now().date(),
            status='published'
        )
        for event in org_events:
            # Avoid duplicates if already in calendar_events
            if not any(getattr(e, 'related_event_id', None) == event.id for e in calendar_events):
                upcoming_events.append(SimpleNamespace(
                    title=event.title,
                    date=event.date,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    location=getattr(event, 'venue', None),
                ))
    else:
        # Performer: add accepted performer events
        accepted_applications = EventApplication.objects.filter(
            performer=profile_user,
            status='accepted',
            event__date__gte=timezone.now().date()
        ).select_related('event')
        performer_events = [app.event for app in accepted_applications]
        for event in performer_events:
            if not any(getattr(e, 'related_event_id', None) == event.id for e in calendar_events):
                upcoming_events.append(SimpleNamespace(
                    title=event.title,
                    date=event.date,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    location=getattr(event, 'venue', None),
                ))
    upcoming_events.sort(key=lambda e: (e.date, e.start_time))
    context = {
        'profile_user': profile_user,
        'availabilities': availabilities,
        'upcoming_events': upcoming_events,
        'now': timezone.now().date(),
    }
    return render(request, 'accounts/user_profile.html', context)

@login_required
def user_list(request):
    users = User.objects.select_related('profile').all()
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role in ['performer', 'organizer']:
        users = users.filter(profile__role=role)
    users = users.order_by('username')
    return render(request, 'accounts/user_list.html', {'users': users})
