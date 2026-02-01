# ===============================
# Django core imports
# ===============================
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
    get_user_model,
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.db import IntegrityError
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.timezone import now

# ===============================
# Python standard library
# ===============================
import csv
import random
import time
import re
import os
from datetime import date, datetime

# ===============================
# Third-party libraries
# ===============================
from reportlab.pdfgen import canvas
import openpyxl
from openpyxl.styles import Font, Alignment
import africastalking

# ===============================
# Local app imports (models)
# ===============================
from .models import (
    User,
    TeacherProfile,
    StudentProfile,
    ParentProfile,
    Classroom,
    AcademicYear,
    Attendance,
    SMSLog,
    Stream,
    SchoolSettings,
)

# ===============================
# Local app imports (forms)
# ===============================
from .forms import (
    TeacherProfileForm,
    SchoolSettingsForm,
    UserUpdateForm,
    AcademicYearForm,
)
from django.template.loader import render_to_string
from xhtml2pdf import pisa


# ===============================
# Local app imports (utils)
# ===============================
from .utils import auto_lock_expired_academic_year



import random
import time
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from attendance_app.utils import send_sms

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.mail import send_mail

from .models import TeacherProfile, Classroom, Stream, User

import africastalking
import logging

logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
User = get_user_model()


def login_view(request):
    # Check if an admin already exists
    admin_exists = User.objects.filter(role='admin').exists()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Optional: auto upgrade superuser to admin if role is not admin
            if user.is_superuser and user.role != 'admin':
                user.role = 'admin'
                user.save()

            login(request, user)

            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'student':
                return redirect('student_dashboard')
            else:
                logout(request)
                messages.error(request, "Invalid role!")
                return redirect('login')
        else:
            messages.error(request, "Invalid username or password!")
            return redirect('login')

    # Pass admin_exists boolean to template
    return render(request, 'attendance_app/login.html', {'admin_exists': admin_exists})





def format_phone_number(phone):

    if not phone:
        return None

    # Remove spaces, dashes, brackets
    phone = re.sub(r"[^\d+]", "", phone)

    # 07XXXXXXXX or 06XXXXXXXX
    if phone.startswith("0") and len(phone) == 10:
        phone = "+255" + phone[1:]

    # 7XXXXXXXX or 6XXXXXXXX
    elif phone.startswith(("6", "7")) and len(phone) == 9:
        phone = "+255" + phone

    # 2557XXXXXXXX
    elif phone.startswith("255") and len(phone) == 12:
        phone = "+" + phone

    # +2557XXXXXXXX (already correct)
    elif phone.startswith("+255") and len(phone) == 13:
        pass

    else:
        return None

    # Final validation
    if phone.startswith(("+2556", "+2557")) and len(phone) == 13:
        return phone

    return None

@never_cache
def register_admin(request):
    # Allow only one admin
    if User.objects.filter(role='admin').exists():
        messages.warning(request, "Admin already exists! Please login.")
        return redirect('login')

    if request.method == "POST":
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Required fields
        if not all([first_name, last_name, email, phone_number, password1, password2]):
            messages.error(request, "All fields are required!")
            return redirect('register_admin')

        # Password check
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register_admin')

        # Email uniqueness
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('register_admin')

        # Phone normalization
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            messages.error(
                request,
                "Phone number must be a valid Tanzanian number (06 or 07)"
            )
            return redirect('register_admin')

        # Phone uniqueness
        if User.objects.filter(phone_number=formatted_phone).exists():
            messages.error(request, "Phone number is already in use!")
            return redirect('register_admin')

        # Create admin
        User.objects.create(
            username=email,              # username = email
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=formatted_phone,
            password=make_password(password1),
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        messages.success(request, "Admin registered successfully! Please login.")
        return redirect('login')

    return render(request, 'attendance_app/register_admin.html')

@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def admin_dashboard(request):
    # All teachers
    teachers = TeacherProfile.objects.all()

    # Total students
    total_students = StudentProfile.objects.count()

    # Total classrooms
    classrooms_count = Classroom.objects.count()

    # Active academic year
    active_year_obj = AcademicYear.objects.filter(is_active=True).first()
    active_year = f"{active_year_obj.year_start}/{active_year_obj.year_end}" if active_year_obj else "N/A"

    context = {
        'teachers': teachers,
        'total_students': total_students,
        'classrooms_count': classrooms_count,
        'active_year': active_year,
    }

    return render(request, 'attendance_app/admin_dashboard.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.conf import settings
import africastalking
import logging

logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "Teacher@123"

@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def register_teacher(request):
    classrooms = Classroom.objects.all()
    
    # Pagination: only 25 teachers per page
    teacher_list = TeacherProfile.objects.select_related('user', 'classroom', 'stream').all().order_by('user__first_name')
    paginator = Paginator(teacher_list, 25)
    page_number = request.GET.get('page')
    teachers = paginator.get_page(page_number)

    if request.method == 'POST':
        try:
            username = request.POST.get('username', '').strip()  # email
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            classroom_id = request.POST.get('classroom')
            stream_id = request.POST.get('stream')

            # ================= EMAIL VALIDATION =================
            if not username or '@' not in username:
                messages.error(request, "Please enter a valid email for username.")
                return redirect('register_teacher')

            # ================= CLASSROOM =================
            try:
                classroom = Classroom.objects.get(id=classroom_id)
            except Classroom.DoesNotExist:
                messages.error(request, "Selected classroom does not exist.")
                return redirect('register_teacher')

            # ================= STREAM & AVAILABILITY =================
            stream = None
            if stream_id:
                try:
                    stream = Stream.objects.get(id=stream_id, classroom=classroom)
                    # Pre-check: ensure no teacher is assigned already
                    if TeacherProfile.objects.filter(stream=stream).exists():
                        messages.warning(
                            request,
                            f"Stream '{stream.name}' in classroom '{classroom.name}' already has a teacher assigned. "
                            "Please choose another stream."
                        )
                        return redirect('register_teacher')
                except Stream.DoesNotExist:
                    messages.error(request, "Selected stream does not exist.")
                    return redirect('register_teacher')

            # ================= USER EXISTS =================
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists. Try a different email.")
                return redirect('register_teacher')

            # ================= PHONE NORMALIZATION =================
            if phone_number:
                phone_number = phone_number.replace(' ', '').replace('-', '')
                if phone_number.startswith('0') and len(phone_number) == 10:
                    phone_number = '+255' + phone_number[1:]
                elif phone_number.startswith(('6', '7')) and len(phone_number) == 9:
                    phone_number = '+255' + phone_number
                elif not phone_number.startswith('+'):
                    phone_number = '+255' + phone_number

            # ================= CREATE USER =================
            user = User.objects.create(
                username=username,
                email=username,
                first_name=first_name,
                last_name=last_name,
                password=make_password(DEFAULT_PASSWORD),
                role='teacher',
                phone_number=phone_number
            )

            # ================= CREATE TEACHER PROFILE =================
            TeacherProfile.objects.create(
                user=user,
                classroom=classroom,
                stream=stream
            )

            # ================= SEND SMS =================
            if phone_number:
                try:
                    africastalking.initialize(
                        username=settings.AFRICASTALKING_USERNAME,
                        api_key=settings.AFRICASTALKING_API_KEY
                    )
                    sms = africastalking.SMS
                    response = sms.send(
                        message=(
                            f"Habari {first_name}, account yako ya Teacher "
                            f"imesajiliwa.\nUsername: {username}\nPassword: {DEFAULT_PASSWORD}"
                        ),
                        recipients=[phone_number],
                        sender_id='School_SMS'
                        
                    )
                    logger.info(f"SMS sent successfully: {response}")
                except Exception as sms_error:
                    logger.error(f"SMS failed: {sms_error}")

            # ================= SEND EMAIL =================
            try:
                from django.core.mail import send_mail
                send_mail(
                    "Your Teacher Account Details",
                    (
                        f"Habari {first_name},\n\n"
                        f"Account yako imesajiliwa.\n"
                        f"Username: {username}\nPassword: {DEFAULT_PASSWORD}\n\n"
                        f"Tafadhali badilisha password mara ya kwanza kuingia."
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [username],
                    fail_silently=True
                )
            except Exception as email_error:
                logger.warning(f"Email failed: {email_error}")

            messages.success(request, f"Teacher {first_name} {last_name} registered successfully!")
            return redirect('register_teacher')

        except Exception as e:
            logger.critical(f"Register Teacher Error: {e}")
            messages.error(request, "Internal server error occurred while registering teacher.")
            return redirect('register_teacher')

    return render(
        request,
        'attendance_app/register_teacher.html',
        {
            'classrooms': classrooms,
            'teachers': teachers
        }
    )





@never_cache
@login_required
def get_streams(request, classroom_id):
    streams = Stream.objects.filter(classroom_id=classroom_id)
    data = {'streams': [{'id': s.id, 'name': s.name} for s in streams]}
    return JsonResponse(data)


@never_cache
@login_required
def teacher_dashboard(request):
    # teacher profile
    teacher_profile = TeacherProfile.objects.get(user=request.user)

    classroom = teacher_profile.classroom
    stream = teacher_profile.stream

    # students under this teacher
    students = StudentProfile.objects.filter(classroom=classroom)
    if stream:
        students = students.filter(stream=stream)

    total_students = students.count()

    # attendance summary
    total_attendance = Attendance.objects.filter(student__in=students).count()
    present_count = Attendance.objects.filter(student__in=students, status='Present').count()
    absent_count = Attendance.objects.filter(student__in=students, status='Absent').count()
    sick_count = Attendance.objects.filter(student__in=students, status='Sick').count()

    # parents related to students
    parents = ParentProfile.objects.filter(student__in=students)

    # recent SMS logs for these students (last 10)
    sms_logs = SMSLog.objects.filter(student__in=students).order_by('-timestamp')[:10]

    context = {
        'teacher': teacher_profile,
        'classroom': classroom,
        'stream': stream,
        'students': students,
        'parents': parents,
        'total_students': total_students,
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'sms_logs': sms_logs,
    }

    return render(request, 'attendance_app/teacher_dashboard.html', context)





@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def register_student(request):

    classroom = None
    stream = None

    # =========================================
    # GET TEACHER CLASSROOM & STREAM (FIXED)
    # =========================================
    if request.user.role == 'teacher':
        teacher = request.user.teacherprofile
        classroom = teacher.classroom
        stream = teacher.stream   

        if not classroom or not stream:
            messages.error(
                request,
                "You are not properly assigned to a classroom and stream."
            )
            return redirect('teacher_dashboard')

    # =========================================
    # FETCH ACADEMIC YEARS
    # =========================================
    active_year = AcademicYear.objects.filter(is_active=True).first()
    academic_years = AcademicYear.objects.all()

    if request.method == 'POST':

        # ===== STUDENT DATA =====
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        password = request.POST.get('password') or "Student@123"
        admission_number = request.POST.get('admission_number')

        academic_year_id = request.POST.get('academic_year')
        academic_year_obj = AcademicYear.objects.filter(
            id=academic_year_id
        ).first() if academic_year_id else active_year

        # =====================================
        # ADMIN SELECTS CLASSROOM & STREAM
        # =====================================
        if request.user.role == 'admin':
            classroom_id = request.POST.get('classroom')
            stream_id = request.POST.get('stream')

            if not classroom_id or not stream_id:
                messages.error(
                    request,
                    "Please select both classroom and stream."
                )
                return redirect('register_student')

            classroom = get_object_or_404(Classroom, id=classroom_id)
            stream = get_object_or_404(Stream, id=stream_id, classroom=classroom)

        # ===== PARENT DATA =====
        parent_full_name = request.POST.get('parent_full_name')
        parent_phone = request.POST.get('parent_phone', '').strip()

        # ===== FORMAT PHONE =====
        parent_phone = parent_phone.replace(' ', '').replace('-', '')

        if parent_phone.startswith('0') and len(parent_phone) == 10:
            parent_phone = '+255' + parent_phone[1:]
        elif parent_phone.startswith(('6', '7')) and len(parent_phone) == 9:
            parent_phone = '+255' + parent_phone

        if not re.match(r'^\+255[67]\d{8}$', parent_phone):
            messages.error(request, "Invalid parent phone number.")
            return redirect('register_student')

        # ===== CHECK ADMISSION NUMBER =====
        if User.objects.filter(username=admission_number).exists():
            messages.error(request, "Admission number already exists.")
            return redirect('register_student')

        # =====================================
        # CREATE STUDENT USER & PROFILE
        # =====================================
        student_user = User.objects.create(
            username=admission_number,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            role='student',
            password=make_password(password)
        )

        student_profile = StudentProfile.objects.create(
            user=student_user,
            classroom=classroom,
            stream=stream,
            admission_number=admission_number,
            academic_year=academic_year_obj
        )

        # =====================================
        # CREATE PARENT USER & PROFILE
        # =====================================
        parent_names = parent_full_name.split(" ", 1)
        parent_first = parent_names[0]
        parent_last = parent_names[1] if len(parent_names) > 1 else ""

        if not User.objects.filter(username=parent_phone).exists():
            parent_user = User.objects.create(
                username=parent_phone,
                first_name=parent_first,
                last_name=parent_last,
                phone_number=parent_phone,
                role='parent',
                password=make_password(parent_phone)
            )

            ParentProfile.objects.create(
                user=parent_user,
                student=student_profile
            )

        messages.success(
            request,
            f"Student {first_name} {last_name} registered in "
            f"{classroom.name} - {stream.name}"
        )

        return redirect('register_student')

  
    # LISTING STUDENTS
    if request.user.role == 'teacher':
        students = StudentProfile.objects.filter(
            classroom=classroom,
            stream=stream
        )
        template = 'attendance_app/register_student_teacher.html'
    else:
        students = StudentProfile.objects.all()
        template = 'attendance_app/register_student_admin.html'

    classrooms = Classroom.objects.all()
    streams = Stream.objects.all()

    return render(request, template, {
        'students': students,
        'classrooms': classrooms,
        'streams': streams,
        'active_year': active_year,
        'academic_years': academic_years,
        'teacher_classroom': classroom,
        'teacher_stream': stream,
    })



@never_cache  
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def manage_classrooms(request):
    academic_years = AcademicYear.objects.filter(is_active=True).order_by('-year_start')

    if request.method == "POST":
        # Safisha input
        name = request.POST.get('name', '').strip()
        year_id = request.POST.get('year')

        # Check input
        if not name or not year_id:
            messages.error(request, "Please provide both classroom name and academic year.")
            return redirect('manage_classrooms')

        year_obj = get_object_or_404(AcademicYear, id=year_id)

        # Check duplicates strictly
        duplicate = Classroom.objects.filter(name__iexact=name, year=year_obj).exists()
        if duplicate:
            messages.error(request, f"Classroom '{name}' already exists for {year_obj}.")
            return redirect('manage_classrooms')

        # CREATE NEW CLASSROOM
        Classroom.objects.create(name=name, year=year_obj)
        messages.success(request, f"Classroom '{name}' added successfully for {year_obj}.")
        return redirect('manage_classrooms')

    # LIST CLASSROOMS
    classrooms = Classroom.objects.all().order_by('year__year_start', 'name')
    return render(request, 'attendance_app/manage_classrooms.html', {
        'classrooms': classrooms,
        'academic_years': academic_years
    })


 
@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def delete_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)

    # Check related students and teachers only
    has_students = classroom.studentprofile_set.exists()
    has_teachers = classroom.teacherprofile_set.exists()

    if request.method == "POST":
        if has_students or has_teachers:
            parts = []
            if has_students:
                parts.append("students")
            if has_teachers:
                parts.append("teachers")
            parts_str = " and ".join(parts)

            messages.error(
                request,
                f"Cannot delete '{classroom.name}' because it has assigned {parts_str}."
            )
        else:
            # No students or teachers → safe to delete
            classroom.delete()
            messages.success(request, f"Classroom '{classroom.name}' deleted successfully.")

    return redirect('manage_classrooms')


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def edit_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    if request.method == "POST":
        new_name = request.POST.get('name', '').strip()
        
        if not new_name:
            messages.error(request, "Classroom name cannot be empty.")
            return redirect('manage_classrooms')

        # Check duplicate within the same academic year
        duplicate = Classroom.objects.filter(
            name__iexact=new_name, 
            year=classroom.year
        ).exclude(id=classroom.id).exists()

        if duplicate:
            messages.error(request, f"Classroom '{new_name}' already exists for {classroom.year}.")
        else:
            classroom.name = new_name
            classroom.save()
            messages.success(request, f"Classroom '{new_name}' updated successfully.")

        return redirect('manage_classrooms')
    
    return render(request, 'attendance_app/edit_classroom.html', {'classroom': classroom})



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def add_stream(request, class_id):
    classroom = get_object_or_404(Classroom, id=class_id)

    if request.method == 'POST':
        stream_name = request.POST.get('stream_name', '').strip()

        if not stream_name:
            messages.error(request, "Stream name cannot be empty.")
            return redirect('manage_classrooms')

        # Check if stream already exists in this classroom (case-insensitive)
        if classroom.streams.filter(name__iexact=stream_name).exists():
            messages.error(request, f"Stream '{stream_name}' already exists in classroom '{classroom.name}'.")
        else:
            Stream.objects.create(name=stream_name, classroom=classroom)
            messages.success(request, f"Stream '{stream_name}' added successfully to classroom '{classroom.name}'.")

    return redirect('manage_classrooms')



@never_cache
@login_required
def academic_years(request):
    auto_lock_expired_academic_year()
    years = AcademicYear.objects.all().order_by('-year_start')
    return render(request, 'attendance_app/academic_years.html', {'years': years})


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def attendance_report(request):
    classroom_id = request.GET.get('classroom')

    attendances = Attendance.objects.select_related(
        'student__user',
        'student__classroom',
        'marked_by__user'
    )

    if classroom_id:
        attendances = attendances.filter(student__classroom_id=classroom_id)

    classrooms = Classroom.objects.all()

    return render(request, 'attendance_app/attendance_report.html', {
        'attendances': attendances,
        'classrooms': classrooms
    })



@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'teacher'])
def sms_logs(request):
    user = request.user

    if user.role == 'admin':
        # Admin aone SMS zote
        logs = SMSLog.objects.all().order_by('-timestamp')
    elif user.role == 'teacher':
        # Teacher aone SMS za wanafunzi wa madarasa yake tu
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
            # Wanafunzi wote wa madarasa ya teacher
            students_in_class = StudentProfile.objects.filter(classroom__in=teacher_profile.classrooms.all())
            logs = SMSLog.objects.filter(student__in=students_in_class).order_by('-timestamp')
        except TeacherProfile.DoesNotExist:
            logs = SMSLog.objects.none()
    else:
        logs = SMSLog.objects.none()

    return render(request, 'attendance_app/sms_logs.html', {
        'sms_logs': logs
    })



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def edit_teacher(request, id):
    try:
        teacher = TeacherProfile.objects.get(id=id)
    except TeacherProfile.DoesNotExist:
        messages.error(request, "Teacher does not exist.")
        return redirect('manage_teachers')

    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        classroom_id = request.POST.get('classroom')
        stream_id = request.POST.get('stream')

        # update user info
        teacher.user.username = username
        teacher.user.first_name = first_name
        teacher.user.last_name = last_name
        teacher.user.save()

        # update classroom
        try:
            classroom = Classroom.objects.get(id=classroom_id)
            teacher.classroom = classroom
        except Classroom.DoesNotExist:
            teacher.classroom = None

        # update stream
        if stream_id:
            try:
                stream = Stream.objects.get(id=stream_id, classroom=teacher.classroom)
                teacher.stream = stream
            except Stream.DoesNotExist:
                teacher.stream = None
        else:
            teacher.stream = None

        teacher.save()
        messages.success(request, "Teacher updated successfully!")
        return redirect('register_teacher')

    # GET request
    streams = Stream.objects.filter(classroom=teacher.classroom) if teacher.classroom else []
    return render(request, 'attendance_app/edit_teacher.html', {
        'teacher': teacher,
        'classrooms': classrooms,
        'streams': streams
    })


@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['admin'])
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, id=teacher_id)
    user_to_delete = teacher.user

    # Delete teacher (user + profile)
    user_to_delete.delete()
    messages.success(request, "Teacher deleted successfully.")

    # If admin deleted their own account, log them out
    if request.user == user_to_delete:
        logout(request)
        return redirect('login')  

    return redirect('register_teacher')



@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def edit_student(request, student_id):
    student = StudentProfile.objects.get(id=student_id)

    if request.method == 'POST':
        student.user.first_name = request.POST.get('first_name')
        student.user.last_name = request.POST.get('last_name')
        stream_id = request.POST.get('stream')
        student.user.gender=request.POST.get('gender')

        student.stream_id = stream_id if stream_id else None

        student.user.save()
        student.save()

        # Return success message for toast
        return JsonResponse({
            'success': True,
            'message': f"{student.user.first_name} {student.user.last_name} updated successfully!"
        })

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def delete_student(request, student_id):
    # Get the student
    student = get_object_or_404(StudentProfile, id=student_id)

    # Delete parents first
    parents = ParentProfile.objects.filter(student=student)
    for parent in parents:
        parent.user.delete()  

    # Delete student (user + profile)
    student.user.delete()  

    messages.success(request, "Student and associated parent(s) deleted successfully.")
    return redirect('register_student')




@never_cache
def forgot_password(request):
    if request.method == "POST":
        try:
            identifier = request.POST.get("identifier", "").strip()

            if not identifier:
                messages.error(request, "Enter email or phone number")
                return redirect("forgot_password")

            # ================= FIND USER =================
            user = (
                User.objects.filter(email=identifier).first()
                or User.objects.filter(phone_number=identifier).first()
            )

            if not user:
                messages.error(request, "User not found")
                return redirect("forgot_password")

            # ================= GENERATE RESET CODE =================
            code = random.randint(100000, 999999)

            request.session["reset_code"] = str(code)
            request.session["reset_user"] = user.id
            request.session["reset_time"] = int(time.time())

            # ================= SEND SMS (PRIMARY) =================
            if user.phone_number:
                phone = user.phone_number.strip()

                # Normalize Tanzania number
                if phone.startswith("0") and len(phone) == 10:
                    phone = "+255" + phone[1:]
                elif phone.startswith(("6", "7")) and len(phone) == 9:
                    phone = "+255" + phone
                elif not phone.startswith("+"):
                    phone = "+255" + phone

                try:
                    sms_sent = send_sms(
                        phone,
                        f"Namba ya kurejesha password ni {code}"
                    )

                    if sms_sent:
                        logger.info(f"Password reset SMS sent to {phone}")
                    else:
                        logger.warning("SMS sending failed")

                except Exception as sms_error:
                    logger.error(f"SMS error: {sms_error}")
            else:
                logger.warning("No phone number, SMS skipped")

            # ================= SEND EMAIL (OPTIONAL) =================
            if user.email:
                try:
                    send_mail(
                        subject="Password Reset Code",
                        message=f"Your password reset code is {code}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True  
                    )
                    logger.info(f"Password reset email sent to {user.email}")
                except Exception as email_error:
                    logger.warning(f"Email error: {email_error}")

            messages.success(
                request,
                "Reset code sent via SMS and Email (if available)"
            )
            return redirect("verify_reset")

        except Exception as e:
            logger.critical(f"Forgot password error: {e}")
            messages.error(request, "Something went wrong. Try again.")
            return redirect("forgot_password")

    # ================= GET REQUEST =================
    return render(request, "attendance_app/forgot_password.html")




def verify_reset(request):
    if request.method == "POST":
        code = request.POST.get("code")
        session_code = request.session.get("reset_code")
        reset_time = request.session.get("reset_time")

        if not session_code or not reset_time:
            messages.error(request, "Session expired")
            return redirect("forgot_password")

        # OTP expires after 5 minutes
        if time.time() - reset_time > 300:
            messages.error(request, "Code expired")
            return redirect("forgot_password")

        if code == session_code:
            return redirect("reset_password")

        messages.error(request, "Invalid code")

    return render(request, "attendance_app/verify_reset.html")




def reset_password(request):
    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("reset_password")

        user_id = request.session.get("reset_user")
        if not user_id:
            messages.error(request, "Session expired")
            return redirect("forgot_password")

        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()

        request.session.flush()

        messages.success(request, "Password reset successful. Please login.")
        return redirect("login")

    return render(request, "attendance_app/reset_password.html")



def send_absent_sms(student):
    try:
        # Pata mzazi
        parent = ParentProfile.objects.get(student=student)
        parent_phone = parent.user.phone_number

        if not parent_phone:
            print(f"No phone number for parent of {student.user.get_full_name()}")
            return

        # Ensure parent phone is +255
        if parent_phone.startswith("0"):
            parent_phone = "+255" + parent_phone[1:]
        elif not parent_phone.startswith("+"):
            parent_phone = "+255" + parent_phone

        # Pata teacher wa classroom ya mwanafunzi
        teacher = TeacherProfile.objects.filter(classroom=student.classroom).first()
        teacher_phone = teacher.user.phone_number if teacher else "N/A"

        # Ensure teacher phone format +255
        if teacher_phone and teacher_phone.startswith("0"):
            teacher_phone = "+255" + teacher_phone[1:]
        elif teacher_phone and not teacher_phone.startswith("+"):
            teacher_phone = "+255" + teacher_phone

        # Prepare SMS
        message = (
            f"HABARI MZAZI: Mtoto wako {student.user.get_full_name()} "
            f"hajafika shuleni leo. "
            f"Tafadhali wasiliana na mwalimu wa darasa kwa namba {teacher_phone}."
        )

        # Africa's Talking SMS
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )
        sms = africastalking.SMS

        response = sms.send(
            message=message,
            recipients=[parent_phone],
            sender_id="School_SMS"
        )
        print("SMS sent:", response)

        # Log SMS
        SMSLog.objects.create(
            student=student,
            parent=parent,
            message=message,
            status='sent'
        )

    except ParentProfile.DoesNotExist:
        print(f"No parent found for student {student.user.get_full_name()}")
    except Exception as e:
        print(f"SMS sending failed: {e}")
        SMSLog.objects.create(
            student=student,
            parent=parent if 'parent' in locals() else None,
            message=message if 'message' in locals() else "",
            status='failed'
        )

@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def mark_attendance(request):

    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream

    if not classroom or not stream:
        messages.error(
            request,
            "You are not assigned to a classroom or stream."
        )
        return redirect('teacher_dashboard')

    # 🔥 FILTER BY CLASSROOM + STREAM
    students_list = StudentProfile.objects.filter(
        classroom=classroom,
        stream=stream,
        status='Active'
    ).order_by('admission_number')

    paginator = Paginator(students_list, 25)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    if request.method == "POST":
        today = timezone.now().date()

        for student in students:  # PAGINATED LOOP
            status = request.POST.get(
                f'attendance_{student.id}', 'present'
            )

            Attendance.objects.update_or_create(
                student=student,
                date=today,
                defaults={
                    'status': status,
                    'marked_by': teacher
                }
            )

            # ===== ABSENT SMS LOGIC =====
            if status == 'absent':
                start = timezone.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end = timezone.now().replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )

                sms_exists = SMSLog.objects.filter(
                    student=student,
                    timestamp__range=(start, end)
                ).exists()

                if not sms_exists:
                    send_absent_sms(student)

        return redirect('view_attendance')

    return render(request, 'attendance_app/mark_attendance.html', {
        'students': students,
        'classroom': classroom,
        'stream': stream,
        'teacher': teacher,
    })



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def teacher_sms_logs(request):

    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream

    if not classroom or not stream:
        messages.error(
            request,
            "You are not assigned to a classroom or stream."
        )
        return redirect('teacher_dashboard')

    logs = SMSLog.objects.filter(
        student__classroom=classroom,
        student__stream=stream,
        student__attendances__marked_by=teacher
    ).select_related(
        'student', 'parent'
    ).distinct().order_by('-timestamp')

    return render(request, 'attendance_app/teacher_sms_logs.html', {
        'logs': logs,
        'teacher': teacher,
        'classroom': classroom,
        'stream': stream,
    })



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def delete_sms_log(request, sms_id):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom

    try:
        sms_log = SMSLog.objects.get(id=sms_id, student__classroom=classroom)
        sms_log.delete()

        # check if AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        else:
            return redirect('teacher_sms_logs')

    except SMSLog.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'SMS log not found'})
        else:
            return redirect('teacher_sms_logs')





@never_cache
@login_required
def view_attendance(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream  # stream ya mwalimu

    # =================== DATE FILTER ===================
    raw_date = request.GET.get("date")
    page_number = request.GET.get("page")

    try:
        selected_date = (
            datetime.strptime(raw_date, "%Y-%m-%d").date()
            if raw_date else now().date()
        )
    except ValueError:
        selected_date = now().date()

    # =================== BASE STUDENTS QUERYSET ===================
    students_qs = StudentProfile.objects.filter(classroom=classroom)

    if stream:
        students_qs = students_qs.filter(stream=stream)

    # =================== ATTENDANCE QUERYSET ===================
    attendance_qs = Attendance.objects.filter(
        student__in=students_qs,
        date=selected_date
    ).select_related("student", "student__user").order_by(
        "student__user__first_name"
    )

    # =================== PAGINATION ===================
    paginator = Paginator(attendance_qs, 25)
    attendance_records = paginator.get_page(page_number)

    # =================== TOTAL SUMMARY ===================
    students_count = students_qs.count()

    total_present = attendance_qs.filter(status='present').count()
    total_absent = attendance_qs.filter(status='absent').count()
    total_sick = attendance_qs.filter(status='sick').count()
    total_records = total_present + total_absent + total_sick

    present_percentage = round((total_present / total_records) * 100, 2) if total_records else 0
    absent_percentage = round((total_absent / total_records) * 100, 2) if total_records else 0
    sick_percentage = round((total_sick / total_records) * 100, 2) if total_records else 0

    # =================== SUMMARY BY GENDER ===================
    male_students = students_qs.filter(user__gender='male')
    female_students = students_qs.filter(user__gender='female')

    male_count = male_students.count()
    female_count = female_students.count()

    male_present = attendance_qs.filter(student__in=male_students, status='present').count()
    male_absent = attendance_qs.filter(student__in=male_students, status='absent').count()
    male_sick = attendance_qs.filter(student__in=male_students, status='sick').count()

    male_total_records = male_present + male_absent + male_sick
    male_present_pct = round((male_present / male_total_records) * 100, 2) if male_total_records else 0
    male_absent_pct = round((male_absent / male_total_records) * 100, 2) if male_total_records else 0
    male_sick_pct = round((male_sick / male_total_records) * 100, 2) if male_total_records else 0

    female_present = attendance_qs.filter(student__in=female_students, status='present').count()
    female_absent = attendance_qs.filter(student__in=female_students, status='absent').count()
    female_sick = attendance_qs.filter(student__in=female_students, status='sick').count()

    female_total_records = female_present + female_absent + female_sick
    female_present_pct = round((female_present / female_total_records) * 100, 2) if female_total_records else 0
    female_absent_pct = round((female_absent / female_total_records) * 100, 2) if female_total_records else 0
    female_sick_pct = round((female_sick / female_total_records) * 100, 2) if female_total_records else 0

    # =================== CONTEXT ===================
    context = {
        "classroom": classroom,
        "stream": stream,
        "teacher": teacher,
        "attendance_records": attendance_records,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "today": now().date(),

        # Total summary
        "students_count": students_count,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_sick": total_sick,
        "present_percentage": present_percentage,
        "absent_percentage": absent_percentage,
        "sick_percentage": sick_percentage,

        # Gender summary
        "male_count": male_count,
        "male_present": male_present,
        "male_absent": male_absent,
        "male_sick": male_sick,
        "male_present_pct": male_present_pct,
        "male_absent_pct": male_absent_pct,
        "male_sick_pct": male_sick_pct,

        "female_count": female_count,
        "female_present": female_present,
        "female_absent": female_absent,
        "female_sick": female_sick,
        "female_present_pct": female_present_pct,
        "female_absent_pct": female_absent_pct,
        "female_sick_pct": female_sick_pct,
    }

    return render(request, "attendance_app/view_attendance.html", context)



@login_required
def attendance_export_pdf(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream

    raw_date = request.GET.get("date")
    try:
        selected_date = (
            datetime.strptime(raw_date, "%Y-%m-%d").date()
            if raw_date else now().date()
        )
    except ValueError:
        selected_date = now().date()

    qs = Attendance.objects.filter(
        student__classroom=classroom,
        date=selected_date
    ).select_related("student", "student__user")

    if stream:
        qs = qs.filter(student__stream=stream)

    html = render_to_string(
        "attendance_app/attendance_pdf.html",
        {
            "records": qs,
            "classroom": classroom,
            "date": selected_date
        }
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename=Attendance_{classroom.name}_{selected_date}.pdf'
    )

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response


@login_required
def attendance_export_excel(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream

    raw_date = request.GET.get("date")
    try:
        selected_date = (
            datetime.strptime(raw_date, "%Y-%m-%d").date()
            if raw_date else now().date()
        )
    except ValueError:
        selected_date = now().date()

    qs = Attendance.objects.filter(
        student__classroom=classroom,
        date=selected_date
    ).select_related("student", "student__user")

    if stream:
        qs = qs.filter(student__stream=stream)

    # ================= CALCULATIONS =================
    total = qs.count()
    present = qs.filter(status="present").count()
    absent = qs.filter(status="absent").count()
    sick = qs.filter(status="sick").count()

    def pct(x):
        return round((x / total) * 100, 1) if total else 0

    male_qs = qs.filter(student__user__gender="male")
    female_qs = qs.filter(student__user__gender="female")

    # ================= EXCEL =================
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    bold = Font(bold=True)
    center = Alignment(horizontal="center")

    row = 1

    # ===== TITLE =====
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    ws.cell(row=row, column=1, value="SMARTPRESENCE – ATTENDANCE REPORT").font = bold
    ws.cell(row=row, column=1).alignment = center
    row += 2

    # ===== CLASS INFO =====
    ws.append([
        "Class:",
        classroom.name,
        "Year:",
        str(classroom.year),  # Fixed: convert AcademicYear object to string
        "Date:",
        selected_date.strftime("%Y-%m-%d")
    ])
    for col in range(1, 7):
        ws.cell(row=row, column=col).font = bold
    row += 2

    # ===== SUMMARY =====
    ws.append(["SUMMARY"])
    ws.cell(row=row, column=1).font = bold
    row += 1

    ws.append(["Total Students", total])
    ws.append(["Present", f"{present} ({pct(present)}%)"])
    ws.append(["Absent", f"{absent} ({pct(absent)}%)"])
    ws.append(["Sick", f"{sick} ({pct(sick)}%)"])
    row += 2

    # ===== GENDER SUMMARY =====
    ws.append(["GENDER SUMMARY"])
    ws.cell(row=row, column=1).font = bold
    row += 1

    ws.append([
        "Male",
        male_qs.count(),
        f"Present {male_qs.filter(status='present').count()}",
        f"Absent {male_qs.filter(status='absent').count()}",
        f"Sick {male_qs.filter(status='sick').count()}",
    ])

    ws.append([
        "Female",
        female_qs.count(),
        f"Present {female_qs.filter(status='present').count()}",
        f"Absent {female_qs.filter(status='absent').count()}",
        f"Sick {female_qs.filter(status='sick').count()}",
    ])

    row += 2

    # ===== TABLE HEADER =====
    headers = ["No", "Admission No", "Student Name", "Gender", "Status", "Date"]
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        ws.cell(row=row, column=col).font = bold
        ws.cell(row=row, column=col).alignment = center
    row += 1

    # ===== TABLE DATA =====
    for i, r in enumerate(qs, start=1):
        ws.append([
            i,
            r.student.admission_number,
            r.student.user.get_full_name(),
            r.student.user.gender.capitalize() if r.student.user.gender else "",
            r.status.capitalize(),
            r.date.strftime("%Y-%m-%d")
        ])

    # ===== COLUMN WIDTH =====
    widths = [6, 18, 28, 12, 14, 14]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    # ===== RESPONSE =====
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename=Attendance_{classroom.name}_{selected_date}.xlsx'
    )

    wb.save(response)
    return response





@never_cache
@login_required
def edit_attendance(request, pk):
    attendance = get_object_or_404(Attendance, id=pk)
    today = now().date()

    # Prevent editing for past days
    if attendance.date < today and request.method == "POST":
        return JsonResponse({
            "success": False,
            "message": "Cannot edit attendance for past days."
        })

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["present", "absent", "sick"]:
            attendance.status = new_status
            attendance.save()
            return JsonResponse({
                "success": True,
                "message": f"Attendance updated to {new_status.capitalize()} successfully."
            })
        return JsonResponse({
            "success": False,
            "message": "Invalid status selected."
        })

    # GET request
    sms_logs = SMSLog.objects.filter(student=attendance.student, timestamp__date=attendance.date)
    can_edit = attendance.date >= today
    return render(request, "attendance_app/edit_attendance_modal.html", {
        "attendance": attendance,
        "sms_logs": sms_logs,
        "can_edit": can_edit
    })


    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["present", "absent", "sick"]:
            attendance.status = new_status
            attendance.save()
            return JsonResponse({
                "success": True,
                "message": f"Attendance updated to {new_status.capitalize()} successfully."
            })
        else:
            return JsonResponse({
                "success": False,
                "message": "Invalid status selected."
            })

    # GET request: fetch SMS logs related to this attendance
    sms_logs = SMSLog.objects.filter(student=attendance.student, timestamp__date=attendance.date)

    return render(
        request,
        "attendance_app/edit_attendance_modal.html",
        {
            "attendance": attendance,
            "sms_logs": sms_logs,
            "can_edit": attendance.date >= today,
        }
    )




@never_cache
@login_required
def my_students(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)

    classroom = teacher.classroom
    stream = teacher.stream
    search = request.GET.get("search", "")

    students_qs = StudentProfile.objects.filter(
        classroom=classroom
    ).select_related("user")

    if stream:
        students_qs = students_qs.filter(stream=stream)

    if search:
        students_qs = students_qs.filter(
            Q(admission_number__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    students_qs = students_qs.order_by("user__first_name")

    paginator = Paginator(students_qs, 25)  # 25 per page
    page_number = request.GET.get("page")
    students = paginator.get_page(page_number)

    context = {
        "students": students,
        "classroom": classroom,
        'teacher': teacher,
        "search": search
    }
    return render(request, "attendance_app/my_students.html", context)




@never_cache
@login_required
def delete_attendance(request, pk):
    """
    Delete attendance via AJAX and return JSON response
    """
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        try:
            attendance = get_object_or_404(Attendance, pk=pk)
            attendance.delete()
            return JsonResponse({
                "success": True,
                "message": "Attendance record deleted successfully."
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Failed to delete: {str(e)}"
            })
    return JsonResponse({
        "success": False,
        "message": "Invalid request."
    }, status=400)



@never_cache
@login_required
def student_profile_modal(request, pk):
    student = get_object_or_404(StudentProfile, id=pk)
    return render(request, "attendance_app/student_profile_modal.html", {
        "student": student
    })




# ================= EXPORT EXCEL =================
@never_cache
@login_required
def export_students_excel(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)

    students = StudentProfile.objects.filter(
        classroom=teacher.classroom
    ).select_related("user")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="students_{teacher.classroom.name}.csv"'

    writer = csv.writer(response)
    writer.writerow(["Admission No", "Name", "Email", "Phone", "Gender", "Classroom"])

    for s in students:
        writer.writerow([
            s.admission_number,
            f"{s.user.first_name} {s.user.last_name}",
            s.user.email,
            getattr(s, 'phone_number', '—'),
            s.user.gender.capitalize() if s.user.gender else '—',
            s.classroom.name
        ])

    return response


# ================= EXPORT PDF =================
@never_cache
@login_required
def export_students_pdf(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)

    students = StudentProfile.objects.filter(
        classroom=teacher.classroom
    ).select_related("user")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="students_{teacher.classroom.name}.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 800, f"Students List - {teacher.classroom.name}")
    p.setFont("Helvetica", 10)

    y = 770
    p.drawString(50, y, "No")
    p.drawString(80, y, "Admission No")
    p.drawString(180, y, "Name")
    p.drawString(330, y, "Email")
    p.drawString(480, y, "Phone")
    p.drawString(550, y, "Gender")
    y -= 20

    for i, s in enumerate(students, start=1):
        p.drawString(50, y, str(i))
        p.drawString(80, y, s.admission_number)
        p.drawString(180, y, f"{s.user.first_name} {s.user.last_name}")
        p.drawString(330, y, s.user.email)
        p.drawString(480, y, getattr(s, 'phone_number', '—'))
        p.drawString(550, y, s.user.gender.capitalize() if s.user.gender else '—')
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
            p.setFont("Helvetica", 10)

    p.showPage()
    p.save()
    return response




@never_cache
@login_required
def teacher_profile_view(request):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    students = StudentProfile.objects.filter(classroom=teacher.classroom) if teacher else []

    profile_success = None
    password_success = None

    if request.method == 'POST':
        profile_form = TeacherProfileForm(request.POST, request.FILES, instance=teacher, user=request.user)
        password_form = PasswordChangeForm(user=request.user, data=request.POST)

        if 'update_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            profile_success = "Profile updated successfully!"
        elif 'change_password' in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            password_success = "Password changed successfully!"
    else:
        profile_form = TeacherProfileForm(instance=teacher, user=request.user)
        password_form = PasswordChangeForm(user=request.user)

    context = {
        'teacher': teacher,
        'students': students,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_success': profile_success,
        'password_success': password_success,
    }
    return render(request, 'attendance_app/teacher_profile.html', context)




@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def resend_sms(request, sms_id):
    sms_log = get_object_or_404(SMSLog, id=sms_id, student__classroom=request.user.teacherprofile.classroom)

    try:
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )
        sms = africastalking.SMS
        response = sms.send(
            message=sms_log.message,
            recipients=[sms_log.parent.user.phone_number],
            sender_id="School_SMS"
        )
        sms_log.status = "sent"
        sms_log.timestamp = timezone.now()
        sms_log.save()
        messages.success(request, "SMS resent successfully!")
    except Exception as e:
        sms_log.status = "failed"
        sms_log.save()
        messages.error(request, f"Failed to resend SMS: {e}")

    return redirect('teacher_sms_logs')

@never_cache
@login_required
def admin_profile(request):
    profile, _ = TeacherProfile.objects.get_or_create(user=request.user)

    # Forms
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    profile_form = TeacherProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=request.user
    )

    settings_obj, _ = SchoolSettings.objects.get_or_create(id=1)
    settings_form = SchoolSettingsForm(
        request.POST or None,
        request.FILES or None,
        instance=settings_obj
    )

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid() and settings_form.is_valid():
            user_form.save()
            profile_form.save()
            settings_form.save()
            messages.success(request, "Profile updated successfully!")
        else:
            messages.error(request, "Please fix the errors below.")

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'settings_form': settings_form,
        'profile': profile,  # for direct access in template
    }
    return render(request, 'attendance_app/admin_profile.html', context)



from django.core.files.storage import default_storage
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import os

@never_cache
@login_required
def school_settings(request):
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)
    form = SchoolSettingsForm(request.POST or None, request.FILES or None, instance=school_settings)

    if request.method == 'POST':
        if form.is_valid():
            # Delete old logo safely
            if 'logo' in request.FILES and school_settings.logo:
                if default_storage.exists(school_settings.logo.name):
                    default_storage.delete(school_settings.logo.name)

            form.save()
            messages.success(request, "School settings updated successfully")
            return redirect('school_settings')
        else:
            messages.error(request, "Failed to update school settings")
            print(form.errors)  # debugging

    return render(request, 'attendance_app/admin_settings.html', {
        'form': form,
        'school_settings': school_settings,
    })




@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def attendance_report_cards(request):
    """
    Show attendance report by cards for each classroom.
    Clicking a card navigates to detailed attendance of that class.
    """
    classrooms = Classroom.objects.all().order_by('year', 'name')

    context = {
        "classrooms": classrooms
    }
    return render(request, "attendance_app/attendance_report_cards.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def view_class_attendance(request, classroom_id):
    """
    Detailed attendance for a single class.
    Filterable by date and stream.
    """
    classroom = get_object_or_404(Classroom, id=classroom_id)
    streams = Stream.objects.filter(classroom=classroom)

    selected_stream_id = request.GET.get("stream")
    raw_date = request.GET.get("date")

    try:
        selected_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else now().date()
    except ValueError:
        selected_date = now().date()

    attendance_qs = Attendance.objects.filter(student__classroom=classroom, date=selected_date)

    if selected_stream_id:
        attendance_qs = attendance_qs.filter(student__stream_id=selected_stream_id)

    attendance_qs = attendance_qs.select_related("student__user", "marked_by__user").order_by("student__user__first_name")

    context = {
        "classroom": classroom,
        "attendance_records": attendance_qs,
        "streams": streams,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "selected_stream_id": int(selected_stream_id) if selected_stream_id else None
    }

    return render(request, "attendance_app/view_class_attendance.html", context)



@never_cache
@login_required
def add_academic_year(request):
    if request.method == 'POST':
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            year_start = form.cleaned_data['year_start']
            year_end = form.cleaned_data['year_end']

            if AcademicYear.objects.filter(
                year_start=year_start,
                year_end=year_end
            ).exists():
                messages.error(request, "Academic Year already exists")
            else:
                form.save()
                messages.success(request, "Academic Year added successfully")
                return redirect('academic_years')
    else:
        form = AcademicYearForm()

    return render(request, 'attendance_app/add_academic_year.html', {'form': form})


@never_cache
@login_required
def edit_academic_year(request, id):
    year = get_object_or_404(AcademicYear, id=id)

    if request.method == "POST":
        year_start = request.POST.get('year_start')

        # convert to int
        try:
            year_start = int(year_start)
        except ValueError:
            messages.error(request, "Start Year must be a number")
            return redirect('academic_years')

        year.year_start = year_start
        year.year_end = year_start + 1  # now safe

        # handle is_active checkbox
        year.is_active = 'is_active' in request.POST

        year.save()
        messages.success(request, f"Academic Year {year.year_start}/{year.year_end} updated successfully")
        return redirect('academic_years')

    return redirect('academic_years')



@never_cache
@login_required
def delete_academic_year(request, id):
    year = get_object_or_404(AcademicYear, id=id)

    if request.method == "POST":
        try:
            year.delete()
            messages.success(request, f"Academic Year {year.year_start}/{year.year_end} deleted successfully.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete Academic Year {year.year_start}/{year.year_end} because it is in use."
            )
        return redirect('academic_years')

    return redirect('academic_years')




@never_cache
@login_required
def generate_academic_year(request):
    current_year = timezone.now().year
    last_year = AcademicYear.objects.order_by('-year_start').first()

    # determine new_start
    if last_year:
        # only allow to generate same year as current if not exists
        if last_year.year_start >= current_year:
            messages.error(request, "You cannot generate an academic year beyond the current year.")
            return redirect('academic_years')
        new_start = last_year.year_start + 1
    else:
        new_start = current_year

    new_end = new_start + 1

    # prevent duplicate years
    if AcademicYear.objects.filter(year_start=new_start, year_end=new_end).exists():
        messages.error(request, f"Academic Year {new_start}/{new_end} already exists")
        return redirect('academic_years')

    # lock previous active year
    AcademicYear.objects.filter(is_active=True).update(is_active=False, is_locked=True)

    # create new academic year
    AcademicYear.objects.create(
        year_start=new_start,
        year_end=new_end,
        is_active=True,
        is_locked=False
    )

    messages.success(request, f"Academic Year {new_start}/{new_end} generated successfully")
    return redirect('academic_years')



@never_cache
@login_required
def academic_year_summary(request):
    years = AcademicYear.objects.all().order_by('-year_start')
    active_year_id = request.GET.get('year')
    active_year = None
    summary_data = []

    if active_year_id:
        try:
            active_year = AcademicYear.objects.get(id=active_year_id)
        except AcademicYear.DoesNotExist:
            active_year = None

    if active_year:
        classrooms = Classroom.objects.filter(year=active_year)
        for classroom in classrooms:
            students = classroom.students.all()
            students_count = students.count()

            # Waelimu waliohusika na classroom hii
            teachers = TeacherProfile.objects.filter(classroom=classroom)

            # Attendance summary kwa students wote wa classroom
            total_present = Attendance.objects.filter(
                student__in=students,
                status='present'
            ).count()
            total_absent = Attendance.objects.filter(
                student__in=students,
                status='absent'
            ).count()
            total_sick = Attendance.objects.filter(
                student__in=students,
                status='sick'
            ).count()

            # Attendance percentage
            total_records = total_present + total_absent + total_sick
            if total_records > 0:
                present_percentage = round((total_present / total_records) * 100, 2)
                absent_percentage = round((total_absent / total_records) * 100, 2)
                sick_percentage = round((total_sick / total_records) * 100, 2)
            else:
                present_percentage = absent_percentage = sick_percentage = 0

            summary_data.append({
                'classroom': classroom,
                'students_count': students_count,
                'teachers': teachers,
                'total_present': total_present,
                'total_absent': total_absent,
                'total_sick': total_sick,
                'present_percentage': present_percentage,
                'absent_percentage': absent_percentage,
                'sick_percentage': sick_percentage,
            })

    context = {
        'years': years,
        'active_year': active_year,
        'summary_data': summary_data,
    }

    return render(request, 'attendance_app/academic_year_summary.html', context)




