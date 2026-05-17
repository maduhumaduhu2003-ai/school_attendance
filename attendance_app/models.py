import re
from io import BytesIO
from PIL import Image
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from cloudinary.models import CloudinaryField
from cloudinary.uploader import destroy

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_phone(value):
    return re.sub(r"[^\d+]", "", value)

def validate_phone_number(value):
    if not value:
        return
    phone = normalize_phone(value)
    if not re.match(r'^\+255[67]\d{8}$', phone):
        raise ValidationError(
            "Phone must be valid Tanzanian number (+2556XXXXXXXX or +2557XXXXXXXX)"
        )

# ============================================================
# USER MODEL (OPTIMIZED)
# ============================================================

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, db_index=True)
    phone_number = models.CharField(
        max_length=15, null=True, blank=True, validators=[validate_phone_number], db_index=True
    )
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female')],
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['username']),
            models.Index(fields=['-date_joined']),
        ]

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone(self.phone_number)
        super().save(*args, **kwargs)

# ============================================================
# ACADEMIC YEAR (OPTIMIZED)
# ============================================================

class AcademicYear(models.Model):
    year_start = models.IntegerField(unique=True, db_index=True)
    year_end = models.IntegerField()
    is_active = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['-year_start']),
        ]

    def clean(self):
        if self.year_end <= self.year_start:
            raise ValidationError("Year End must be greater than Year Start")

    def save(self, *args, **kwargs):
        self.year_end = self.year_start + 1

        with transaction.atomic():
            if self.pk:
                old = AcademicYear.objects.select_for_update().get(pk=self.pk)
                if old.is_locked:
                    raise ValidationError("This academic year is locked and cannot be modified.")

            if self.is_active:
                AcademicYear.objects.select_for_update().update(is_active=False)

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year_start}/{self.year_end}"

# ============================================================
# CLASSROOM & STREAM 
# ============================================================


class Classroom(models.Model):

    FORM_CHOICES = [
        ('Form I', 'Form I'),
        ('Form II', 'Form II'),
        ('Form III', 'Form III'),
        ('Form IV', 'Form IV'),
        ('Form V', 'Form V'),
        ('Form VI', 'Form VI'),
    ]

    name = models.CharField(
        max_length=20,
        choices=FORM_CHOICES,
        db_index=True
    )

    year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='classrooms',
        db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'year'],
                name='unique_class_per_year'
            )
        ]

        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['name']),
        ]

        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.year})"


class Stream(models.Model):

    STREAM_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('F', 'F'),
        ('G', 'G'),
        ('H', 'H'),
        ('I', 'I'),
        ('J', 'J'),
        ('K', 'K'),
        ('L', 'L'),
        ('M', 'M'),
        ('N', 'N'),
        ('O', 'O'),
        ('P', 'P'),
        ('Q', 'Q'),
        ('R', 'R'),
        ('S', 'S'),
        ('T', 'T'),
        ('U', 'U'),
        ('V', 'V'),
        ('W', 'W'),
        ('X', 'X'),
        ('Y', 'Y'),
        ('Z', 'Z'),
    ]

    name = models.CharField(
        max_length=5,
        choices=STREAM_CHOICES,
        db_index=True
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='streams',
        db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'classroom'],
                name='unique_stream_per_class'
            )
        ]

        indexes = [
            models.Index(fields=['classroom']),
            models.Index(fields=['name']),
        ]

        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.classroom.name} {self.name}"

# ============================================================
# TEACHER PROFILE 
# ============================================================

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile', db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return self.user.get_full_name() or self.user.username

# ============================================================
# STUDENT PROFILE 
# ============================================================

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', db_index=True)
    admission_number = models.CharField(max_length=20, unique=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.admission_number} - {self.user.get_full_name()}"

# ============================================================
# ENROLLMENT 
# ============================================================

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Graduated', 'Graduated'),
        ('Promoted', 'Promoted'),
        ('Inactive', 'Inactive'),
    ]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, 
        related_name='enrollments', null=True, blank=True, db_index=True
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.PROTECT, 
        null=True, blank=True, related_name='class_enrollments', db_index=True
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, 
        null=True, blank=True, db_index=True
    )
    class_teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='class_enrollments', db_index=True
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='class_enrollments', db_index=True
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active', db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'academic_year'], name='unique_student_per_year'),
        
            models.UniqueConstraint(
                fields=['class_teacher', 'academic_year', 'classroom', 'stream'],
                condition=models.Q(class_teacher__isnull=False),
                name='unique_teacher_per_class_stream_per_year'
            )
        ]
        indexes = [
            models.Index(fields=['academic_year']),
            models.Index(fields=['student']),
            models.Index(fields=['status']),
            models.Index(fields=['classroom']),
            models.Index(fields=['class_teacher']),
            models.Index(fields=['academic_year', 'status']),
            models.Index(fields=['classroom', 'academic_year']),
            models.Index(fields=['class_teacher', 'academic_year']),
        ]

    def clean(self):
        if self.stream and self.stream.classroom != self.classroom:
            raise ValidationError("Stream must belong to selected classroom")

    def __str__(self):
        return f"{self.student} - {self.classroom} ({self.academic_year})"

# ============================================================
# PARENT PROFILE 
# ============================================================

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile', db_index=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parents', db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'student'], name='unique_parent_student')
        ]
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} (Parent of {self.student.user.get_full_name()})"

# ============================================================
# ATTENDANCE 
# ============================================================

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('sick', 'Sick'),
    ]

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, 
        related_name='attendances', null=True, blank=True, db_index=True
    )
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, 
        related_name='attendances', null=True, blank=True, db_index=True
    )
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    marked_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'date', 'enrollment'],
                name='unique_attendance_per_day'
            )
        ]
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['status']),
            models.Index(fields=['student']),
            models.Index(fields=['enrollment']),
            models.Index(fields=['marked_by']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['student', 'date']),
            models.Index(fields=['enrollment', 'date']),
        ]

# ============================================================
# SMS LOGS (OPTIMIZED)
# ============================================================

class SMSLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, db_index=True)
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, db_index=True)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['student']),
            models.Index(fields=['parent']),
            models.Index(fields=['-timestamp']),
        ]

# ============================================================
# SCHOOL SETTINGS 
# ============================================================

class SchoolSettings(models.Model):
    school_name = models.CharField(max_length=200, db_index=True)
    logo = CloudinaryField('school_logo', blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['school_name']),
        ]

    def clean(self):
        if not self.pk and SchoolSettings.objects.exists():
            raise ValidationError("Only one SchoolSettings instance allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.pk:
            old = SchoolSettings.objects.filter(pk=self.pk).first()
            if old and old.logo and old.logo != self.logo:
                destroy(old.logo.public_id)

        if self.logo and hasattr(self.logo, 'file') and isinstance(self.logo.file, InMemoryUploadedFile):
            try:
                img = Image.open(self.logo.file)
                if img.height > 300 or img.width > 300:
                    img.thumbnail((300, 300))
                    buffer = BytesIO()
                    img.save(buffer, format='PNG', optimize=True, quality=70)
                    buffer.seek(0)

                    self.logo = InMemoryUploadedFile(
                        buffer,
                        'ImageField',
                        self.logo.name,
                        'image/png',
                        buffer.getbuffer().nbytes,
                        None
                    )
            except Exception:
                pass

        super().save(*args, **kwargs)