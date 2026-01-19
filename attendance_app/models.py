from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from django.core.exceptions import ValidationError
from django.utils import timezone
import os



class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], null=True, blank=True)


class AcademicYear(models.Model):
    year_start = models.IntegerField(unique=True)
    year_end = models.IntegerField()
    is_active = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.year_end <= self.year_start:
            raise ValidationError("Year End must be greater than Year Start")

    def save(self, *args, **kwargs):
        # Ensure year_end = year_start + 1
        self.year_end = self.year_start + 1

        # Only one active year at a time
        if self.is_active:
            AcademicYear.objects.exclude(id=self.id).update(is_active=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year_start}/{self.year_end}"


class Classroom(models.Model):
    name = models.CharField(max_length=50)
    year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='classrooms')

    def __str__(self):
        return f"{self.name} ({self.year})"


class Stream(models.Model):
    name = models.CharField(max_length=50)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='streams')

    def __str__(self):
        return f"{self.name} ({self.classroom.name})"



class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    stream = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Futa picha ya zamani kama kuna mpya
        if self.pk:
            old = TeacherProfile.objects.filter(pk=self.pk).first()
            if old and old.profile_picture:
                if self.profile_picture and old.profile_picture != self.profile_picture:
                    if os.path.isfile(old.profile_picture.path):
                        os.remove(old.profile_picture.path)

        super().save(*args, **kwargs)

        # Resize image (endelea kama ulivyokuwa)
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            max_size = (300, 300)

            if img.height > 300 or img.width > 300:
                img.thumbnail(max_size)
                img.save(self.profile_picture.path, optimize=True, quality=70)

    def __str__(self):
        return self.user.get_full_name()



class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.ForeignKey(
        Classroom, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='students'  
    )
    stream = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    admission_number = models.CharField(max_length=20)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='students')
    status = models.CharField(max_length=10, default='Active')

    def __str__(self):
        return self.user.get_full_name()



class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parents')

    def __str__(self):
        return self.user.get_full_name()


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('sick', 'Sick'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('student', 'date')


class SMSLog(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='sms_logs')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='sms_logs')
    message = models.TextField()
    status = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.status}"




class SchoolSettings(models.Model):
    school_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='school/logo/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Angalia kama kuna existing record
        if self.pk:
            old = SchoolSettings.objects.filter(pk=self.pk).first()
            if old and old.logo:
                # Futa old logo ikiwa kuna mpya
                if self.logo and old.logo != self.logo:
                    if os.path.isfile(old.logo.path):
                        os.remove(old.logo.path)

        super().save(*args, **kwargs)

        # Resize image ikiwa ipo
        if self.logo:
            img = Image.open(self.logo.path)
            max_size = (300, 300)
            if img.height > 300 or img.width > 300:
                img.thumbnail(max_size)
                img.save(self.logo.path, optimize=True, quality=70)

    def __str__(self):
        return self.school_name
