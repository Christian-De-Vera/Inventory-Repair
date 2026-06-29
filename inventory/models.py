from django.db import models
from datetime import date
import uuid
import random
import string
import os
import qrcode
from io import BytesIO

# ============================================
# 1. Category Model
# ============================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Department(models.Model):
    """Managed list of departments"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Departments"
    
    def __str__(self):
        return self.name


# ============================================
# 2. Location Model
# ============================================
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


# ============================================
# 3. Person Model
# ============================================
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


# ============================================
# 4. Custom Field Model
# ============================================
class CustomField(models.Model):
    """Define custom fields that can be added to items"""
    FIELD_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Multi-line Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Yes/No'),
        ('url', 'URL/Link'),
        ('email', 'Email'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Field name (e.g., 'Warranty Info', 'Supplier')")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    is_required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.CharField(max_length=200, blank=True, null=True)
    sort_order = models.IntegerField(default=0, help_text="Order in which fields appear")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


# ============================================
# 5. Item Model (main model)
# ============================================
class Item(models.Model):
    # Unique Code
    item_code = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    
    # Basic info
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Kitting (Parent-Child)
    parent_item = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='children',
                                   help_text="The assembly or kit this item belongs to")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
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
    
    # QR code (text field)
    qr_code = models.CharField(max_length=255, blank=True, unique=True, null=True)
    
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)

    # Acquisition tracking
    acquisition_date = models.DateField(blank=True, null=True, verbose_name="Acquisition Date")
    end_of_life_date = models.DateField(blank=True, null=True, verbose_name="End of Life (EOL) Date", 
                                        help_text="The date when this item should be retired or replaced")
    
    # Cost tracking
    acquisition_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Acquisition Cost")
    
    # Auto timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Prevent self-parenting
        if self.parent_item and self.pk == self.parent_item.pk:
            raise ValidationError({'parent_item': "An item cannot be its own parent."})
        
        # Prevent circularity
        if self.parent_item:
            curr = self.parent_item
            while curr is not None:
                if curr.pk == self.pk:
                    raise ValidationError({'parent_item': "Circular reference detected in kit structure."})
                curr = curr.parent_item

    def get_all_children(self):
        """Recursively get all descendants of this item (children, grandchildren, etc.)"""
        descendants = []
        # Using a stack to traverse the tree iteratively
        stack = list(self.children.all())
        while stack:
            node = stack.pop()
            descendants.append(node)
            # Add this node's children to the stack to continue traversal
            stack.extend(node.children.all())
        return descendants

    def get_ancestors(self):
        """Returns a list of ancestors from the root down to the immediate parent."""
        ancestors = []
        curr = self.parent_item
        while curr:
            ancestors.append(curr)
            curr = curr.parent_item
        return ancestors[::-1]

    @property
    def is_kit(self):
        """Returns True if the item has children (is a parent)."""
        return self.children.all().exists()

    @property
    def is_component(self):
        """Returns True if the item belongs to a parent kit."""
        return self.parent_item is not None

    def save(self, *args, **kwargs):
        # Generate unique code if not already set
        if not self.item_code:
            self.item_code = self.generate_unique_code()

        is_new = self.pk is None
        old_location = None

        if not is_new:
            try:
                old_item = Item.objects.get(pk=self.pk)
                old_location = old_item.location
                
                # Check if image is being replaced
                if old_item.image and old_item.image != self.image:
                    other_items = Item.objects.filter(image=old_item.image).exclude(id=self.pk).count()
                    if other_items == 0:
                        try:
                            if os.path.isfile(old_item.image.path):
                                old_item.image.delete(save=False)
                        except (OSError, FileNotFoundError):
                            pass
            except Item.DoesNotExist:
                pass
        super().save(*args, **kwargs)

        # Record location history if it's a new item or location has changed
        if is_new or old_location != self.location:
            LocationHistory.objects.create(
                item=self,
                location=self.location
            )
    
    def delete(self, *args, **kwargs):
        # Check if other items use the same image before deleting
        if self.image:
            other_items = Item.objects.filter(image=self.image).exclude(id=self.id).count()
            if other_items == 0:
                try:
                    if os.path.isfile(self.image.path):
                        os.remove(self.image.path)
                except Exception as e:
                    print(f"Error deleting image: {e}")
        
        super().delete(*args, **kwargs)
    
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
    
    def get_total_value(self):
        """Calculate total value (quantity * acquisition_cost)"""
        if self.acquisition_cost:
            return self.quantity * self.acquisition_cost
        return 0
    
    def get_custom_fields_dict(self):
        """Get all custom field values as a dictionary"""
        result = {}
        for cv in self.custom_values.all():
            result[cv.field.name] = cv.get_value()
        return result
    
    def get_custom_field_value(self, field_name):
        """Get value for a specific custom field by name"""
        try:
            cv = self.custom_values.get(field__name=field_name)
            return cv.get_value()
        except CustomFieldValue.DoesNotExist:
            return None
    
    # NEW METHOD: Generate QR code image for download
    def get_qr_code_image(self):
        """Generate QR code image as BytesIO for the item code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.item_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes


# ============================================
# 6. Location History Model
# ============================================
class LocationHistory(models.Model):
    """Tracks movement history of items between locations"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='location_history')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    moved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-moved_at']
        verbose_name_plural = "Location Histories"

    def __str__(self):
        loc_name = self.location.name if self.location else "Unknown/None"
        return f"{self.item.name} moved to {loc_name} on {self.moved_at.strftime('%Y-%m-%d')}"


# ============================================
# 7. Custom Field Value Model
# ============================================
class CustomFieldValue(models.Model):
    """Store values for custom fields on specific items"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='custom_values')
    field = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    value_text = models.TextField(blank=True, null=True)
    value_number = models.FloatField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value_boolean = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['item', 'field']
    
    def get_value(self):
        """Return the value based on field type"""
        if self.field.field_type in ['text', 'textarea', 'url', 'email']:
            return self.value_text
        elif self.field.field_type == 'number':
            return self.value_number
        elif self.field.field_type == 'date':
            return self.value_date
        elif self.field.field_type == 'boolean':
            return self.value_boolean
        return None
    
    def set_value(self, value):
        """Set the value based on field type"""
        if self.field.field_type in ['text', 'textarea', 'url', 'email']:
            self.value_text = str(value) if value else None
        elif self.field.field_type == 'number':
            self.value_number = float(value) if value else None
        elif self.field.field_type == 'date':
            self.value_date = value if value else None
        elif self.field.field_type == 'boolean':
            self.value_boolean = bool(value)
        self.save()
    
    def __str__(self):
        return f"{self.item.name} - {self.field.name}: {self.get_value()}"


