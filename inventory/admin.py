from django.contrib import admin
from .models import Category, Location, Person, Item, CustomField, CustomFieldValue, LocationHistory, Department
from django.utils.html import format_html

class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'field_type', 'is_required', 'is_active', 'sort_order')
    list_filter = ('field_type', 'is_required', 'is_active')
    search_fields = ('name',)
    list_editable = ('sort_order', 'is_active')
    fieldsets = (
        ('Field Definition', {
            'fields': ('name', 'field_type', 'is_required', 'is_active', 'sort_order')
        }),
        ('Display Options', {
            'fields': ('placeholder', 'help_text')
        }),
    )

class CustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ('item', 'field', 'get_value')
    list_filter = ('field',)
    search_fields = ('item__name', 'field__name')

admin.site.register(CustomField, CustomFieldAdmin)
admin.site.register(CustomFieldValue, CustomFieldValueAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

class DepartmentAdmin(admin.ModelAdmin):
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
    list_filter = ('category', 'department', 'status', 'location', 'person_accountable')
    search_fields = ('item_code', 'name', 'description', 'serial_no')
    readonly_fields = ('item_code',)
# In the ItemAdmin class, update the fieldsets:
    fieldsets = (
        ('Unique Information', {
            'fields': ('item_code',)
        }),
        ('Basic Information', {
            'fields': ('name', 'description', 'parent_item', 'category', 'department', 'serial_no', 'quantity', 'status')
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

class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'location', 'moved_at')
    list_filter = ('location', 'moved_at')
    search_fields = ('item__name', 'item__item_code')
    readonly_fields = ('moved_at',)

admin.site.register(Category, CategoryAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(LocationHistory, LocationHistoryAdmin)