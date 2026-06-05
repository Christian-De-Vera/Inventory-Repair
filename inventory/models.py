from django.db import models
from django import forms
from datetime import date
import uuid
import random
import string

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Location(models.Model):
    """Pre-defined locations that can be managed like categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Locations"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Person(models.Model):
    """Person accountable for items"""
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Persons"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Item(models.Model):
    # Unique Code
    item_code = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    
    # Basic info
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Serial Number
    serial_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial No", help_text="Item's serial number (if applicable)")
    
    # Quantity tracking
    quantity = models.PositiveIntegerField(default=1, help_text="Number of identical items")
    
    # Status choices
    STATUS_CHOICES = [
        ('available', 'Active'),
        ('in_repair', 'In Repair'),
        ('decommissioned', 'Decommissioned'),
        ('lost', 'Lost'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Location tracking
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Person accountable
    person_accountable = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Person Accountable", related_name='items')
    
    # QR code
    qr_code = models.CharField(max_length=255, blank=True, unique=True, null=True)
    
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)

    def generate_unique_code(self):
        """Generate a unique item code that's almost impossible to duplicate"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%y%m%d')
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = Item.objects.filter(created_at__gte=today_start).count() + 1
        sequential = str(today_count).zfill(4)
        
        code = f"ICT-{timestamp}-{sequential}-{random_part}"
        
        if Item.objects.filter(item_code=code).exists():
            code = f"ICT-{uuid.uuid4().hex[:8].upper()}"
        
        return code
    
    def save(self, *args, **kwargs):
        # Generate unique code if not already set
        if not self.item_code:
            self.item_code = self.generate_unique_code()
        
        # Delete old image if replacing with new one
        if self.pk:
            try:
                old_item = Item.objects.get(pk=self.pk)
                if old_item.image and old_item.image != self.image:
                    old_item.image.delete(save=False)
            except Item.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete image file when item is deleted
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    # Acquisition tracking
    acquisition_date = models.DateField(blank=True, null=True, verbose_name="Acquisition Date")
    end_of_life_date = models.DateField(blank=True, null=True, verbose_name="End of Life (EOL) Date")
    
    # Cost tracking
    acquisition_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Acquisition Cost")
    
    # Auto timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        base = f"{self.item_code} - {self.name}"
        if self.quantity > 1:
            base = f"{base} (x{self.quantity})"
        if self.serial_no:
            base = f"{base} [SN: {self.serial_no}]"
        return base
    
    def is_expiring_soon(self):
        """Check if item is within 30 days of end of life"""
        if self.end_of_life_date:
            from datetime import date, timedelta
            days_left = (self.end_of_life_date - date.today()).days
            return days_left <= 30 and days_left >= 0
        return False
    
    def is_expired(self):
        """Check if item has passed its end of life date"""
        if self.end_of_life_date:
            from datetime import date
            return self.end_of_life_date < date.today()
        return False
    
    def get_days_until_eol(self):
        """Get number of days until end of life"""
        if self.end_of_life_date:
            from datetime import date
            days_left = (self.end_of_life_date - date.today()).days
            return days_left
        return None
    
    def get_status_badge_class(self):
        """Return CSS class for status badge based on EOL"""
        if self.is_expired():
            return 'status-expired'
        elif self.is_expiring_soon():
            return 'status-warning'
        return self.status
    
    def get_total_value(self):
        """Calculate total value (quantity * acquisition_cost)"""
        if self.acquisition_cost:
            return self.quantity * self.acquisition_cost
        return 0

# Item Form
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'description', 'category', 'serial_no', 'quantity', 'status', 'location', 'person_accountable', 'image', 
                  'acquisition_date', 'end_of_life_date', 'acquisition_cost']
        widgets = {
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
            'end_of_life_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1}),
            'acquisition_cost': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'serial_no': forms.TextInput(attrs={'placeholder': 'e.g., SN123456789'}),
        }