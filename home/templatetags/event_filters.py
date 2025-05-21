from django import template

register = template.Library()

@register.filter
def filter_by_performer(applications, performer):
    return applications.filter(performer=performer)

@register.filter
def filter_by_talent(applications, talent):
    return applications.filter(talent_type=talent) 