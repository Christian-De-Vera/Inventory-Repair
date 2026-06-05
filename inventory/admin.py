from django.contrib import admin
from .models import Category, Location, Person, Item
from django.utils.html import format_html

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'department', 'contact_number', 'created_at')
    search_fields = ('name', 'email', 'department')
    list_filter = ('department', 'created_at')
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'department', 'contact_number')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)

class ItemAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'name', 'category', 'serial_no', 'quantity', 'location', 'person_accountable', 'status', 'acquisition_date', 'created_at')
    list_filter = ('category', 'status', 'location', 'person_accountable')
    search_fields = ('item_code', 'name', 'description', 'serial_no')
    readonly_fields = ('item_code',)
# In the ItemAdmin class, update the fieldsets:
    fieldsets = (
        ('Unique Information', {
            'fields': ('item_code',)
        }),
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'serial_no', 'quantity', 'status')
        }),
        ('Accountability', {
            'fields': ('location', 'person_accountable')
        }),
        ('Image', {
            'fields': ('image',)
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Acquisition & Lifecycle', {
            'fields': ('acquisition_date', 'end_of_life_date', 'acquisition_cost')
        })
    )
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Image'

admin.site.register(Category, CategoryAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Item, ItemAdmin)