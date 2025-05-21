from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Event, Category, Venue, EventTalent, EventApplication, Availability, WebsiteAnalytics, UserActivity
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.urls import reverse
from accounts.utils import create_notification
from accounts.models import Profile

# Create your views here.

def debug_user(request):
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            return HttpResponse(f"""
                User is authenticated: {request.user.is_authenticated}<br>
                Username: {request.user.username}<br>
                Profile exists: True<br>
                Profile role: {profile.role}<br>
                Is organizer: {profile.role == 'organizer'}<br>
            """)
        except Exception as e:
            return HttpResponse(f"""
                User is authenticated: {request.user.is_authenticated}<br>
                Username: {request.user.username}<br>
                Error accessing profile: {str(e)}<br>
            """)
    else:
        return HttpResponse("User is not authenticated")

def landing_page(request):
    context = {}
    if request.user.is_authenticated:
        context['notification_count'] = request.user.notifications.filter(is_read=False).count()
    return render(request, 'home/landing_page.html', context)

def event_list(request, username=None):
    if username:
        from django.contrib.auth.models import User
        calendar_user = get_object_or_404(User, username=username)
    else:
        calendar_user = request.user
        
    # Get all published events for the event list view
    events = Event.objects.filter(status='published')
    
    # Apply filters
    category = request.GET.get('category')
    date = request.GET.get('date')
    location = request.GET.get('location')
    search = request.GET.get('search')
    
    if category:
        events = events.filter(category_id=category)
    if date:
        events = events.filter(date=date)
    if location:
        events = events.filter(venue__city__icontains=location)
    if search:
        events = events.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    categories = Category.objects.all()
    venues = Venue.objects.all()
    is_owner = request.user.is_authenticated and request.user == calendar_user
    
    # Check if this is a calendar view
    is_calendar_view = request.path.startswith('/calendar/')
    
    context = {
        'events': events,
        'categories': categories,
        'venues': venues,
        'current_category': category,
        'current_date': date,
        'current_location': location,
        'current_search': search,
        'is_organizer': request.user.is_authenticated and request.user.profile.role == 'organizer',
        'is_performer': request.user.is_authenticated and request.user.profile.role == 'performer',
        'calendar_username': calendar_user.username if calendar_user else None,
        'is_owner': is_owner,
        'is_calendar_view': is_calendar_view,
    }
    
    # Use different templates for calendar and event list views
    template = 'home/event_list.html' if is_calendar_view else 'home/events.html'
    return render(request, template, context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    talent_needs = event.talent_needs.all()
    accepted_performers = EventApplication.objects.filter(
        event=event,
        status='accepted'
    ).select_related('performer', 'talent_type')
    
    context = {
        'event': event,
        'talent_needs': talent_needs,
        'accepted_performers': accepted_performers,
        'is_organizer': request.user.is_authenticated and request.user.profile.role == 'organizer',
        'is_performer': request.user.is_authenticated and request.user.profile.role == 'performer',
    }
    return render(request, 'home/event_detail.html', context)

@login_required
def create_event(request):
    if request.user.profile.role != 'organizer':
        messages.error(request, 'Only organizers can create events.')
        return redirect('event_list')
    
    if request.method == 'POST':
        # Handle form submission
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        venue_id = request.POST.get('venue')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        allow_manual_invites = request.POST.get('allow_manual_invites') == 'on'
        action = request.POST.get('action')
        
        # Create event
        event = Event.objects.create(
            title=title,
            description=description,
            category_id=category_id,
            venue_id=venue_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            organizer=request.user,
            status='draft' if action == 'draft' else 'published',
            allow_manual_invites=allow_manual_invites
        )
        
        # Handle talent needs
        talent_types = request.POST.getlist('talent_type[]')
        quantities = request.POST.getlist('quantity_needed[]')
        descriptions = request.POST.getlist('talent_description[]')
        
        for i in range(len(talent_types)):
            EventTalent.objects.create(
                event=event,
                talent_type=talent_types[i],
                quantity_needed=quantities[i],
                description=descriptions[i]
            )
        
        # Create notification for the organizer
        create_notification(
            user=request.user,
            notification_type='event',
            title='Event Created Successfully',
            message=f'Your event "{event.title}" has been created and is now {event.get_status_display().lower()}.',
            link=reverse('event_detail', args=[event.id])
        )
        
        messages.success(request, 'Event created successfully!')
        return redirect('event_detail', event_id=event.id)
    
    context = {
        'categories': Category.objects.all(),
        'venues': Venue.objects.all(),
        'talent_types': EventTalent.TALENT_TYPE_CHOICES,
    }
    return render(request, 'home/event_form.html', context)

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.user != event.organizer:
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        # Handle form submission
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.category_id = request.POST.get('category')
        event.venue_id = request.POST.get('venue')
        event.date = request.POST.get('date')
        event.start_time = request.POST.get('start_time')
        event.end_time = request.POST.get('end_time')
        event.allow_manual_invites = request.POST.get('allow_manual_invites') == 'on'
        action = request.POST.get('action')
        event.status = 'draft' if action == 'draft' else 'published'
        event.save()
        
        # Handle talent needs
        event.talent_needs.all().delete()  # Remove existing talent needs
        talent_types = request.POST.getlist('talent_type[]')
        quantities = request.POST.getlist('quantity_needed[]')
        descriptions = request.POST.getlist('talent_description[]')
        
        for i in range(len(talent_types)):
            EventTalent.objects.create(
                event=event,
                talent_type=talent_types[i],
                quantity_needed=quantities[i],
                description=descriptions[i]
            )
        
        messages.success(request, 'Event updated successfully!')
        return redirect('event_detail', event_id=event.id)
    
    context = {
        'event': event,
        'categories': Category.objects.all(),
        'venues': Venue.objects.all(),
        'talent_types': EventTalent.TALENT_TYPE_CHOICES,
    }
    return render(request, 'home/event_form.html', context)

@login_required
def apply_for_event(request, event_id, talent_id):
    if request.user.profile.role != 'performer':
        messages.error(request, 'Only performers can apply for events.')
        return redirect('event_detail', event_id=event_id)
    
    event = get_object_or_404(Event, id=event_id)
    talent_need = get_object_or_404(EventTalent, id=talent_id, event=event)
    
    # Check if already applied
    if EventApplication.objects.filter(
        event=event,
        performer=request.user,
        talent_type=talent_need
    ).exists():
        messages.error(request, 'You have already applied for this position.')
        return redirect('event_detail', event_id=event_id)
    
    # Create application
    application = EventApplication.objects.create(
        event=event,
        performer=request.user,
        talent_type=talent_need,
        status='pending'
    )
    
    # Create notification for the performer
    create_notification(
        user=request.user,
        notification_type='application',
        title='Application Submitted',
        message=f'You have successfully applied for the position of {talent_need.get_talent_type_display()} in "{event.title}".',
        link=reverse('event_detail', args=[event.id])
    )
    
    # Create notification for the organizer
    create_notification(
        user=event.organizer,
        notification_type='application',
        title='New Application Received',
        message=f'{request.user.username} has applied for the position of {talent_need.get_talent_type_display()} in your event "{event.title}".',
        link=reverse('event_detail', args=[event.id])
    )
    
    messages.success(request, 'Application submitted successfully!')
    return redirect('event_detail', event_id=event_id)

@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.user != event.organizer:
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('event_detail', event_id=event.id)
    
    if event.status != 'draft':
        messages.error(request, 'Only draft events can be deleted.')
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Draft event deleted successfully.')
        return redirect('event_list')
    
    return redirect('event_detail', event_id=event.id)

@login_required
def withdraw_application(request, event_id, talent_id):
    if request.user.profile.role != 'performer':
        messages.error(request, 'Only performers can withdraw applications.')
        return redirect('event_detail', event_id=event_id)
    
    event = get_object_or_404(Event, id=event_id)
    talent_need = get_object_or_404(EventTalent, id=talent_id, event=event)
    
    application = get_object_or_404(
        EventApplication,
        event=event,
        performer=request.user,
        talent_type=talent_need,
        status='pending'
    )
    
    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Application withdrawn successfully.')
    
    return redirect('event_detail', event_id=event_id)

@login_required
def update_application_status(request, event_id, application_id, new_status):
    event = get_object_or_404(Event, id=event_id)
    
    if request.user != event.organizer:
        messages.error(request, 'You do not have permission to update application status.')
        return redirect('event_detail', event_id=event_id)
    
    application = get_object_or_404(EventApplication, id=application_id, event=event)
    
    if request.method == 'POST':
        if new_status in ['accepted', 'rejected']:
            old_status = application.status
            application.status = new_status
            application.save()
            
            # Create notification for the performer
            create_notification(
                user=application.performer,
                notification_type='application',
                title=f'Application {new_status.title()}',
                message=f'Your application for {application.talent_type.get_talent_type_display()} in "{event.title}" has been {new_status}.',
                link=reverse('event_detail', args=[event.id])
            )
            
            messages.success(request, f'Application {new_status} successfully.')
        else:
            messages.error(request, 'Invalid status update.')
    
    return redirect('event_detail', event_id=event_id)

def events_json(request, username=None):
    from django.contrib.auth.models import User
    try:
        if username:
            user = get_object_or_404(User, username=username)
        else:
            user = request.user
            
        # Events where user is organizer
        organizer_events = Event.objects.filter(status='published', organizer=user)
        
        # Events where user is an accepted performer
        performer_event_ids = EventApplication.objects.filter(
            performer=user, status='accepted'
        ).values_list('event_id', flat=True)
        performer_events = Event.objects.filter(status='published', id__in=performer_event_ids)
        
        data = []
        
        # Add organizer events
        for event in organizer_events:
            data.append({
                'id': f'organizer-{event.id}',
                'title': f"[Organizing] {event.title}",
                'start': f"{event.date}T{event.start_time}",
                'end': f"{event.date}T{event.end_time}",
                'url': f"/events/{event.id}/",
                'backgroundColor': '#2563eb',  # blue
                'borderColor': '#1d4ed8',
                'display': 'block'
            })
        
        # Add performer events
        for event in performer_events:
            data.append({
                'id': f'performer-{event.id}',
                'title': f"[Performing] {event.title}",
                'start': f"{event.date}T{event.start_time}",
                'end': f"{event.date}T{event.end_time}",
                'url': f"/events/{event.id}/",
                'backgroundColor': '#22c55e',  # green
                'borderColor': '#16a34a',
                'display': 'block'
            })
            
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def availability_json(request, username=None):
    from django.contrib.auth.models import User
    try:
        if username:
            user = get_object_or_404(User, username=username)
        else:
            user = request.user
            
        availabilities = Availability.objects.filter(user=user)
        data = []
        
        for avail in availabilities:
            data.append({
                'id': f'avail-{avail.id}',
                'title': avail.note or 'Available',
                'start': f"{avail.date}T{avail.start_time}",
                'end': f"{avail.date}T{avail.end_time}",
                'backgroundColor': '#38bdf8',  # light blue
                'borderColor': '#0ea5e9',
                'display': 'background'
            })
            
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
def create_availability(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        note = data.get('note', '')

        # Validate times
        try:
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid date or time format.'}, status=400)

        if end_dt <= start_dt:
            return JsonResponse({'success': False, 'error': 'End time must be after start time.'}, status=400)

        avail = Availability.objects.create(
            user=request.user,
            date=date,
            start_time=start_time,
            end_time=end_time,
            note=note
        )
        return JsonResponse({'success': True, 'id': avail.id})
    return JsonResponse({'success': False}, status=400)

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get or create today's analytics
    today = timezone.now().date()
    analytics, created = WebsiteAnalytics.objects.get_or_create(date=today)
    
    # Update analytics
    analytics.total_users = User.objects.count()
    analytics.total_events = Event.objects.count()
    analytics.total_applications = EventApplication.objects.count()
    analytics.active_events = Event.objects.filter(status='published', date__gte=today).count()
    analytics.completed_events = Event.objects.filter(date__lt=today).count()
    
    # Calculate new items today
    analytics.new_users_today = User.objects.filter(date_joined__date=today).count()
    analytics.new_events_today = Event.objects.filter(created_at__date=today).count()
    analytics.new_applications_today = EventApplication.objects.filter(created_at__date=today).count()
    
    analytics.save()
    
    # Get active tab
    active_tab = request.GET.get('tab', 'overview')
    
    context = {
        'active_tab': active_tab,
        'analytics': analytics,
        'recent_activities': UserActivity.objects.all()[:10],
    }
    
    # Add tab-specific data
    if active_tab == 'users':
        context['users'] = User.objects.select_related('profile').all()
    elif active_tab == 'events':
        context['events'] = Event.objects.select_related('organizer').all()
    elif active_tab == 'reports':
        # Get data for charts
        last_30_days = timezone.now() - timedelta(days=30)
        
        # User growth data
        user_growth = User.objects.filter(
            date_joined__gte=last_30_days
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Event statistics
        event_stats = Event.objects.filter(
            created_at__gte=last_30_days
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Application trends
        application_trends = EventApplication.objects.filter(
            created_at__gte=last_30_days
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        context.update({
            'user_growth': list(user_growth),
            'event_stats': list(event_stats),
            'application_trends': list(application_trends)
        })
    
    return render(request, 'home/admin_dashboard.html', context)
