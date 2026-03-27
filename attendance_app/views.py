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
from attendance_app.utils import send_sms

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.conf import settings

from .models import TeacherProfile, Classroom, Stream, User, Enrollment

import africastalking
import logging
from math import radians, cos, sin, sqrt, atan2
from django.core.files.storage import default_storage



logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
User = get_user_model()


# School GPS coordinates
SCHOOL_LAT = -6.92673
SCHOOL_LNG = 37.56749
MAX_DISTANCE_METERS = 1000


def distance_in_meters(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points (meters)"""
    try:
        R = 6371000
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c
    except Exception:
        return None
    
@never_cache
def login_view(request):
    admin_exists = User.objects.filter(role='admin').exists()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')

        # ✅ VALIDATE LOCATION INPUT
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            messages.error(request, "Location error: allow GPS access.")
            return redirect('login')

        # ✅ CALCULATE DISTANCE
        distance = distance_in_meters(lat, lng, SCHOOL_LAT, SCHOOL_LNG)

        if distance is None:
            messages.error(request, "Could not calculate distance.")
            return redirect('login')

        if distance > MAX_DISTANCE_METERS:
            messages.error(request, "Access denied: you are outside school area.")
            return redirect('login')

        # ✅ AUTHENTICATE USER
        user = authenticate(request, username=username, password=password)

        if not user:
            messages.error(request, "Invalid username or password!")
            return redirect('login')

        # ✅ FIX ROLE FOR SUPERUSER
        if user.is_superuser and user.role != 'admin':
            user.role = 'admin'
            user.save()

        login(request, user)

        # ✅ ROLE REDIRECTION
        role_redirects = {
            'admin': 'admin_dashboard',
            'teacher': 'teacher_dashboard',
            'student': 'student_dashboard',
        }

        if user.role in role_redirects:
            return redirect(role_redirects[user.role])

        logout(request)
        messages.error(request, "Invalid role!")
        return redirect('login')

    return render(request, 'attendance_app/login.html', {
        'admin_exists': admin_exists
    })


def format_phone_number(phone):
    if not phone:
        return None

    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("0") and len(phone) == 10:
        phone = "+255" + phone[1:]

    elif phone.startswith(("6", "7")) and len(phone) == 9:
        phone = "+255" + phone

    elif phone.startswith("255") and len(phone) == 12:
        phone = "+" + phone

    elif phone.startswith("+255") and len(phone) == 13:
        pass
    else:
        return None

    if phone.startswith(("+2556", "+2557")) and len(phone) == 13:
        return phone

    return None

@never_cache
def register_admin(request):

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

        classroom_id = request.POST.get('classroom')
        stream_id = request.POST.get('stream')

        # ✅ VALIDATIONS
        if not all([first_name, last_name, email, phone_number, password1, password2]):
            messages.error(request, "All fields are required!")
            return redirect('register_admin')

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register_admin')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('register_admin')

        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            messages.error(request, "Invalid Tanzanian phone number!")
            return redirect('register_admin')

        if User.objects.filter(phone_number=formatted_phone).exists():
            messages.error(request, "Phone already used!")
            return redirect('register_admin')

        # ✅ CREATE ADMIN USER
        admin_user = User.objects.create(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=formatted_phone,
            password=make_password(password1),
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        classroom = Classroom.objects.filter(id=classroom_id).first()
        stream = Stream.objects.filter(id=stream_id).first()

        TeacherProfile.objects.create(
            user=admin_user,
            classroom=classroom,
            stream=stream
        )

        messages.success(request, "Admin created successfully!")
        return redirect('login')

    return render(request, 'attendance_app/register_admin.html', {
        'classrooms': Classroom.objects.all(),
        'streams': Stream.objects.all(),
    })

@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def admin_dashboard(request):

    active_year = AcademicYear.objects.filter(is_active=True).first()

    total_students = StudentProfile.objects.count()
    classrooms_count = Classroom.objects.count()
    teachers = TeacherProfile.objects.select_related('user')

    context = {
        'teachers': teachers,
        'total_students': total_students,
        'classrooms_count': classrooms_count,
        'active_year': str(active_year) if active_year else "N/A",
    }

    return render(request, 'attendance_app/admin_dashboard.html', context)


logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "Teacher@123"


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def manage_teacher(request):
    classrooms = Classroom.objects.all()

    teacher_list = TeacherProfile.objects.select_related(
        'user', 'classroom', 'stream'
    ).order_by('user__first_name')

    paginator = Paginator(teacher_list, 25)
    teachers = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'attendance_app/manage_teacher.html',
        {
            'classrooms': classrooms,
            'teachers': teachers
        }
    )
    
@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def register_teacher(request):
    classrooms = Classroom.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        classroom_id = request.POST.get('classroom')
        stream_id = request.POST.get('stream')

        # ===== EMAIL VALIDATION =====
        if not username or '@' not in username:
            messages.error(request, "Please enter a valid email.")
            return redirect('register_teacher')

        # ===== CLASSROOM =====
        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            messages.error(request, "Classroom not found.")
            return redirect('register_teacher')

        # ===== STREAM =====
        stream = None
        if stream_id:
            try:
                stream = Stream.objects.get(id=stream_id, classroom=classroom)

                if TeacherProfile.objects.filter(stream=stream).exists():
                    messages.warning(request, "This stream already has a teacher.")
                    return redirect('register_teacher')

            except Stream.DoesNotExist:
                messages.error(request, "Stream not found.")
                return redirect('register_teacher')

        # ===== USER EXISTS =====
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register_teacher')

        # ===== PHONE NORMALIZATION =====
        if phone_number:
            phone_number = phone_number.replace(' ', '').replace('-', '')

            if phone_number.startswith('0') and len(phone_number) == 10:
                phone_number = '+255' + phone_number[1:]
            elif phone_number.startswith(('6', '7')) and len(phone_number) == 9:
                phone_number = '+255' + phone_number
            elif not phone_number.startswith('+'):
                phone_number = '+255' + phone_number

        # ===== CREATE USER =====
        try:
            user = User.objects.create(
                username=username,
                email=username,
                first_name=first_name,
                last_name=last_name,
                password=make_password(DEFAULT_PASSWORD),
                role='teacher',
                phone_number=phone_number
            )

            TeacherProfile.objects.create(
                user=user,
                classroom=classroom,
                stream=stream
            )

        except IntegrityError:
            messages.error(request, "Database error occurred.")
            return redirect('register_teacher')

        # ===== SEND SMS =====
        if phone_number:
            try:
                africastalking.initialize(
                    username=settings.AFRICASTALKING_USERNAME,
                    api_key=settings.AFRICASTALKING_API_KEY
                )

                sms = africastalking.SMS
                sms.send(
                    message=(
                        f"Habari {first_name}, account yako ya Mwalimu "
                        f"imesajiliwa.\nUsername: {username}\nPassword: {DEFAULT_PASSWORD}"
                    ),
                    recipients=[phone_number],
                    sender_id='School_SMS'
                )

            except Exception as e:
                logger.error(f"SMS failed: {e}")

        messages.success(
            request,
            f"Teacher {first_name} {last_name} registered successfully!"
        )

        return redirect('register_teacher')  

    return render(
        request,
        'attendance_app/register_teacher.html',
        {
            'classrooms': classrooms
        }
    )


def get_streams(request, classroom_id):
    streams = Stream.objects.filter(classroom_id=classroom_id)

    # chagua tu streams ambazo hazina teacher
    available_only = request.GET.get('available_only')
    if available_only == '1':
        streams = streams.exclude(teacherprofile__isnull=False)

    data = {'streams': [{'id': s.id, 'name': s.name} for s in streams]}
    return JsonResponse(data)


def get_students_by_teacher_scope(classroom, stream=None, academic_year=None):
    """Return students linked to the class/stream via Enrollment (not direct student fields)."""
    qs = StudentProfile.objects.filter(
        enrollments__classroom=classroom,
        enrollments__status='Active'
    )
    if stream:
        qs = qs.filter(enrollments__stream=stream)
    if academic_year:
        qs = qs.filter(enrollments__academic_year=academic_year)
    return qs.distinct()


@never_cache
@login_required
def teacher_dashboard(request):
    # teacher profile
    teacher_profile = TeacherProfile.objects.get(user=request.user)

    classroom = teacher_profile.classroom
    stream = teacher_profile.stream

    # students under this teacher (via Enrollment relations)
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    total_students = students.count()

    # attendance summary (Attendance has classroom/stream/academic_year, but filter from student list keeps consistency)
    total_attendance = Attendance.objects.filter(student__in=students).count()
    present_count = Attendance.objects.filter(student__in=students, status='present').count()
    absent_count = Attendance.objects.filter(student__in=students, status='absent').count()
    sick_count = Attendance.objects.filter(student__in=students, status='sick').count()

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
def register_student_admin(request):
    active_year = AcademicYear.objects.filter(is_active=True).first()
    academic_years = AcademicYear.objects.all()
    classrooms = Classroom.objects.all()
    streams = Stream.objects.all()

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        password = request.POST.get('password') or "Student@123"
        admission_number = request.POST.get('admission_number')

        academic_year_id = request.POST.get('academic_year')
        academic_year_obj = AcademicYear.objects.filter(id=academic_year_id).first() if academic_year_id else active_year

        classroom_id = request.POST.get('classroom')
        stream_id = request.POST.get('stream')

        if not classroom_id or not stream_id:
            messages.error(request, "Please select both classroom and stream.")
            return redirect('register_student_admin')

        classroom = get_object_or_404(Classroom, id=classroom_id)
        stream = get_object_or_404(Stream, id=stream_id, classroom=classroom)

        parent_full_name = request.POST.get('parent_full_name')
        parent_phone = request.POST.get('parent_phone', '').strip()

        # FORMAT PHONE
        parent_phone = parent_phone.replace(' ', '').replace('-', '')
        if parent_phone.startswith('0') and len(parent_phone) == 10:
            parent_phone = '+255' + parent_phone[1:]
        elif parent_phone.startswith(('6', '7')) and len(parent_phone) == 9:
            parent_phone = '+255' + parent_phone

        if not re.match(r'^\+255[67]\d{8}$', parent_phone):
            messages.error(request, "Invalid parent phone number.")
            return redirect('register_student_admin')

        if User.objects.filter(username=admission_number).exists():
            messages.error(request, "Admission number already exists.")
            return redirect('register_student_admin')

        # ✅ CREATE STUDENT USER
        student_user = User.objects.create(
            username=admission_number,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            role='student',
            password=make_password(password)
        )

        # ✅ CREATE PROFILE (NO CLASSROOM HERE)
        student_profile = StudentProfile.objects.create(
            user=student_user,
            admission_number=admission_number
        )

        # ✅ CREATE ENROLLMENT (HAPA NDIPO CLASS INAWEKWA)
        Enrollment.objects.create(
            student=student_profile,
            classroom=classroom,
            stream=stream,
            academic_year=academic_year_obj,
            status='Active'
        )

        # CREATE PARENT
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

        messages.success(request, f"Student {first_name} {last_name} registered successfully.")
        return redirect('register_student_admin')

    return render(request, 'attendance_app/register_student_admin.html', {
        'classrooms': classrooms,
        'streams': streams,
        'academic_years': academic_years,
        'active_year': active_year,
    })
    
    
@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def manage_student(request):
    students = StudentProfile.objects.all()
    classrooms = Classroom.objects.all()
    streams = Stream.objects.all()
    academic_years = AcademicYear.objects.all()
    active_year = AcademicYear.objects.filter(is_active=True).first()

    classroom_id = request.GET.get('classroom')
    stream_id = request.GET.get('stream')
    year_id = request.GET.get('academic_year')

    if classroom_id:
        students = students.filter(enrollments__classroom_id=classroom_id)

    if stream_id:
        students = students.filter(enrollments__stream_id=stream_id)

    if year_id:
        students = students.filter(enrollments__academic_year_id=year_id)

    students = students.distinct()

    return render(request, 'attendance_app/manage_student.html', {
        'students': students,
        'classrooms': classrooms,
        'streams': streams,
        'academic_years': academic_years,
        'active_year': active_year,
    })


@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher'])
def register_student_teacher(request):
    # Support both names during transition to avoid AttributeError
    teacher = getattr(request.user, 'teacher_profile', None) or getattr(request.user, 'teacherprofile', None)

    if not teacher:
        messages.error(request, "Teacher profile not found. Contact admin to complete your account setup.")
        return redirect('teacher_dashboard')

    classroom = teacher.classroom
    stream = teacher.stream

    if not classroom or not stream:
        messages.error(request, "You are not properly assigned.")
        return redirect('teacher_dashboard')

    active_year = AcademicYear.objects.filter(is_active=True).first()
    academic_years = AcademicYear.objects.all()

    #  LIST STUDENTS USING ENROLLMENT
    students = StudentProfile.objects.filter(
        enrollments__classroom=classroom,
        enrollments__stream=stream
    ).distinct()

    if request.method == 'POST':
        # ================= EXCEL IMPORT =================
        if 'import_excel' in request.POST and request.FILES.get('excel_file'):
            import pandas as pd
            df = pd.read_excel(request.FILES['excel_file'])

            for _, row in df.iterrows():
                admission_number = str(row['admission_number'])

                if User.objects.filter(username=admission_number).exists():
                    continue

                student_user = User.objects.create(
                    username=admission_number,
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    gender=row['gender'],
                    role='student',
                    password=make_password("Student@123")
                )

                student_profile = StudentProfile.objects.create(
                    user=student_user,
                    admission_number=admission_number
                )

                
                Enrollment.objects.create(
                    student=student_profile,
                    classroom=classroom,
                    stream=stream,
                    academic_year=active_year,
                    status='Active'
                )

            messages.success(request, "Excel imported successfully.")
            return redirect('register_student_teacher')

        # ================= MANUAL =================
        admission_number = request.POST.get('admission_number')

        if User.objects.filter(username=admission_number).exists():
            messages.error(request, "Admission number exists.")
            return redirect('register_student_teacher')

        student_user = User.objects.create(
            username=admission_number,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            gender=request.POST.get('gender'),
            role='student',
            password=make_password(request.POST.get('password') or "Student@123")
        )

        student_profile = StudentProfile.objects.create(
            user=student_user,
            admission_number=admission_number
        )

        Enrollment.objects.create(
            student=student_profile,
            classroom=classroom,
            stream=stream,
            academic_year=active_year,
            status='Active'
        )

        # Parent information handling
        parent_full_name = request.POST.get('parent_full_name', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()

        if parent_full_name and parent_phone:
            parent_phone_clean = parent_phone.replace(' ', '').replace('-', '')
            if parent_phone_clean.startswith('0') and len(parent_phone_clean) == 10:
                parent_phone_clean = '+255' + parent_phone_clean[1:]
            elif parent_phone_clean.startswith(('6', '7')) and len(parent_phone_clean) == 9:
                parent_phone_clean = '+255' + parent_phone_clean

            if re.match(r'^\+255[67]\d{8}$', parent_phone_clean):
                parent_names = parent_full_name.split(' ', 1)
                parent_first = parent_names[0]
                parent_last = parent_names[1] if len(parent_names) > 1 else ''

                parent_user, created = User.objects.get_or_create(
                    username=parent_phone_clean,
                    defaults={
                        'first_name': parent_first,
                        'last_name': parent_last,
                        'phone_number': parent_phone_clean,
                        'role': 'parent',
                        'password': make_password(parent_phone_clean)
                    }
                )

                ParentProfile.objects.get_or_create(
                    user=parent_user,
                    student=student_profile
                )
            else:
                messages.warning(request, 'Invalid parent phone number format. Student saved, but parent not linked.')

        messages.success(request, "Student registered successfully.")
        return redirect('register_student_teacher')

    return render(request, 'attendance_app/register_student_teacher.html', {
        'students': students,
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
    has_students = classroom.students.exists()
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
        'marked_by__user'
    )

    if classroom_id:
        attendances = attendances.filter(classroom_id=classroom_id)

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
        logs = SMSLog.objects.all().order_by('-timestamp')
    elif user.role == 'teacher':
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
            active_year = AcademicYear.objects.filter(is_active=True).first()
            students_in_class = get_students_by_teacher_scope(
                classroom=teacher_profile.classroom,
                stream=teacher_profile.stream,
                academic_year=active_year
            )
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
        return redirect('manage_teacher')

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
        return redirect('manage_teacher')

    # GET request
    streams = []
    if teacher.classroom:
        # streams available (no teacher)
        available_streams = Stream.objects.filter(classroom=teacher.classroom).exclude(
            teacherprofile__isnull=False
        )
        # include current teacher stream
        if teacher.stream and teacher.stream not in available_streams:
            streams = list(available_streams) + [teacher.stream]
        else:
            streams = list(available_streams)

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

    return redirect('manage_teacher')





@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def edit_student_page(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    streams = Stream.objects.all()
    classrooms = Classroom.objects.all()
    
    parent = student.parents.first() if student.parents.exists() else None

    if request.method == 'POST':
        # Student info
        student.user.first_name = request.POST.get('first_name', student.user.first_name)
        student.user.last_name = request.POST.get('last_name', student.user.last_name)
        student.user.gender = request.POST.get('gender', student.user.gender)
        student.admission_number = request.POST.get('admission_number', student.admission_number)

        # Class & Stream
        classroom_id = request.POST.get('classroom')
        student.classroom = Classroom.objects.get(id=classroom_id) if classroom_id else None

        stream_id = request.POST.get('stream')
        student.stream = Stream.objects.get(id=stream_id) if stream_id else None

        student.user.save()
        student.save()

        # Parent info
        if parent:
            full_name = request.POST.get('parent_full_name', '').strip()
            if full_name:
                names = full_name.split(' ', 1)
                parent.user.first_name = names[0]
                parent.user.last_name = names[1] if len(names) > 1 else ''

            raw_phone = request.POST.get('parent_phone')
            if raw_phone:
                try:
                    parent.user.phone_number = format_phone_number(raw_phone)
                except Exception:
                    pass  # unaweza kuweka messages.error hapa

            parent.user.save()

        return redirect('manage_student')

    return render(request, 'attendance_app/edit_student_page.html', {
        'student': student,
        'streams': streams,
        'classrooms': classrooms,
        'parent': parent,
    })
    

@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def edit_student_teacher(request, student_id):
    try:
        student = get_object_or_404(StudentProfile, id=student_id)
        streams = Stream.objects.all()
        classrooms = Classroom.objects.all()
        parent = student.parents.first() if student.parents.exists() else None

        if request.method == 'POST':
            # ---------------- student info ----------------
            student.user.first_name = request.POST.get('first_name', student.user.first_name)
            student.user.last_name = request.POST.get('last_name', student.user.last_name)
            student.user.gender = request.POST.get('gender', student.user.gender)
            student.admission_number = request.POST.get('admission_number', student.admission_number)

            # ---------------- class & stream only admin ----------------
            if request.user.role == 'admin':
                classroom_id = request.POST.get('classroom')
                if classroom_id:
                    student.classroom = Classroom.objects.filter(id=classroom_id).first() or student.classroom

                stream_id = request.POST.get('stream')
                if stream_id:
                    student.stream = Stream.objects.filter(id=stream_id).first() or student.stream

            student.user.save()
            student.save()

            # ---------------- parent info ----------------
            if parent:
                full_name = request.POST.get('parent_full_name', '').strip()
                if full_name:
                    names = full_name.split(' ', 1)
                    parent.user.first_name = names[0]
                    parent.user.last_name = names[1] if len(names) > 1 else ''

                raw_phone = request.POST.get('parent_phone')
                if raw_phone:
                    try:
                        parent.user.phone_number = format_phone_number(raw_phone)
                    except Exception:
                        pass

                parent.user.save()

            messages.success(request, "Student updated successfully.")
            return redirect('my_students')

        return render(request, 'attendance_app/edit_student_teacher.html', {
            'student': student,
            'streams': streams,
            'classrooms': classrooms,
            'parent': parent,
            'is_admin': request.user.role == 'admin',
        })

    except Exception as e:
        logger.error(f"Error in edit_student_teacher ({student_id}): {e}")
        messages.error(request, "Unable to update student. Please try again.")
        return redirect('my_students')


@never_cache
@login_required
@user_passes_test(lambda u: u.role in ['teacher', 'admin'])
def delete_student(request, student_id):
    try:
        # Get the student
        student = get_object_or_404(StudentProfile, id=student_id)

        # Delete parents first
        parents = ParentProfile.objects.filter(student=student)
        for parent in parents:
            parent.user.delete()

        # Delete student (user + profile)
        student.user.delete()

        messages.success(request, "Student and associated parent(s) deleted successfully.")
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        messages.error(request, "Failed to delete student. Please try again.")

    if request.user.role == "teacher":
        return redirect("my_students")
    else:
        return redirect("manage_student")



@never_cache
def forgot_password(request):
    if request.method == "POST":
        try:
            identifier = request.POST.get("identifier", "").strip()

            if not identifier:
                messages.error(request, "Enter email or phone number")
                return redirect("forgot_password")

            # ================= FORMAT PHONE =================
            formatted_phone = format_phone_number(identifier)

            # ================= FIND USER =================
            user = (
                User.objects.filter(email=identifier).first()
                or User.objects.filter(phone_number=formatted_phone).first()
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
                phone = format_phone_number(user.phone_number)  # 👈 HAPA NDIO CALL

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

            return redirect("verify_reset")

        except Exception as e:
            logger.critical(f"Forgot password error: {e}")
            messages.error(request, "Something went wrong. Try again.")
            return redirect("forgot_password")

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



def normalize_parent_phone(parent_phone):
    if not parent_phone:
        return None

    parent_phone = re.sub(r"[^\d+]", "", parent_phone)

    if parent_phone.startswith("0") and len(parent_phone) == 10:
        parent_phone = "+255" + parent_phone[1:]
    elif parent_phone.startswith(("6", "7")) and len(parent_phone) == 9:
        parent_phone = "+255" + parent_phone
    elif parent_phone.startswith("255") and len(parent_phone) == 12:
        parent_phone = "+" + parent_phone

    if re.match(r"^\+255[67]\d{8}$", parent_phone):
        return parent_phone

    return None


def send_absent_sms(student, teacher=None):
    parents = ParentProfile.objects.filter(student=student)

    if not parents.exists():
        logger.warning(f"No parent found for student {student.user.get_full_name()}")
        return False

    if teacher is None:
        active_year = AcademicYear.objects.filter(is_active=True).first()
        classroom_ids = student.enrollments.filter(academic_year=active_year, status='Active').values_list('classroom_id', flat=True)
        teacher = TeacherProfile.objects.filter(classroom_id__in=classroom_ids).first()

    teacher_phone = teacher.user.phone_number if teacher and teacher.user.phone_number else "N/A"

    message_template = (
        f"HABARI MZAZI: Mtoto wako {student.user.get_full_name()} "
        f"hajafika shuleni leo. "
        f"Tafadhali wasiliana na mwalimu wa darasa kwa namba {teacher_phone}."
    )

    sent_any = False

    for parent in parents:
        parent_phone_raw = parent.user.phone_number
        parent_phone = normalize_parent_phone(parent_phone_raw)

        if not parent_phone:
            logger.warning(f"Invalid parent phone number for parent {parent.user.get_full_name()} ({parent_phone_raw})")
            SMSLog.objects.create(
                student=student,
                parent=parent,
                message=message_template,
                status='failed'
            )
            continue

        try:
            sms_sent = send_sms(parent_phone, message_template)
            status = 'sent' if sms_sent else 'failed'

            SMSLog.objects.create(
                student=student,
                parent=parent,
                message=message_template,
                status=status
            )

            if sms_sent:
                logger.info(f"SMS sent for student {student.id}, parent {parent.id}: {parent_phone}")
                sent_any = True
            else:
                logger.error(f"SMS failed for student {student.id}, parent {parent.id}: {parent_phone}")

        except Exception as e:
            logger.error(f"SMS sending exception for student {student.id}, parent {parent.id}: {e}")
            SMSLog.objects.create(
                student=student,
                parent=parent,
                message=message_template,
                status='failed'
            )

    return sent_any


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

    # FILTER BY CLASSROOM AND STREAM via Enrollment
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_list = get_students_by_teacher_scope(classroom, stream, academic_year=active_year).order_by('admission_number')

    paginator = Paginator(students_list, 25)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    if request.method == "POST":
        today = timezone.localdate()


        for student in students:  # PAGINATED LOOP
            status = request.POST.get(
                f'attendance_{student.id}', 'present'
            )

            Attendance.objects.update_or_create(
                student=student,
                date=today,
                academic_year=active_year,
                defaults={
                    'status': status,
                    'marked_by': teacher,
                    'classroom': classroom,
                    'stream': stream,
                    'academic_year': active_year
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
                    try:
                        sms_ok = send_absent_sms(student, teacher=teacher)
                        if not sms_ok:
                            messages.warning(request, f"Could not send absent SMS for {student.user.get_full_name()}. Check parent number or SMS service.")
                    except Exception as e:
                        logger.error(f"Unexpected error sending absent SMS for {student.id}: {e}")
                        messages.warning(request, f"Could not send absent SMS for {student.user.get_full_name()}. Check system logs.")

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

    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_in_class = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    logs = SMSLog.objects.filter(
        student__in=students_in_class
    ).select_related(
        'student', 'parent'
    ).order_by('-timestamp')

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
    stream = teacher.stream
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_in_class = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    try:
        sms_log = get_object_or_404(SMSLog, id=sms_id, student__in=students_in_class)
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
    stream = teacher.stream

    # =================== DATE FILTER (TZ SAFE) ===================
    raw_date = request.GET.get("date")
    page_number = request.GET.get("page")

    if raw_date:
        try:
            selected_date = datetime.strptime(
                raw_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    # =================== BASE STUDENTS QUERYSET (Enrollment relation) ===================
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_qs = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    # =================== ATTENDANCE QUERYSET ===================
    attendance_qs = Attendance.objects.filter(
        student__in=students_qs,
        date=selected_date
    ).select_related(
        "student",
        "student__user"
    ).order_by(
        "student__user__first_name"
    )

    # =================== PAGINATION ===================
    paginator = Paginator(attendance_qs, 25)
    attendance_records = paginator.get_page(page_number)

    # =================== TOTAL SUMMARY ===================
    students_count = students_qs.count()

    total_present = attendance_qs.filter(status="present").count()
    total_absent = attendance_qs.filter(status="absent").count()
    total_sick = attendance_qs.filter(status="sick").count()

    total_records = total_present + total_absent + total_sick

    present_percentage = round((total_present / total_records) * 100, 2) if total_records else 0
    absent_percentage = round((total_absent / total_records) * 100, 2) if total_records else 0
    sick_percentage = round((total_sick / total_records) * 100, 2) if total_records else 0

    # =================== SUMMARY BY GENDER ===================
    male_students = students_qs.filter(user__gender="male")
    female_students = students_qs.filter(user__gender="female")

    male_count = male_students.count()
    female_count = female_students.count()

    male_present = attendance_qs.filter(student__in=male_students, status="present").count()
    male_absent = attendance_qs.filter(student__in=male_students, status="absent").count()
    male_sick = attendance_qs.filter(student__in=male_students, status="sick").count()

    male_total = male_present + male_absent + male_sick
    male_present_pct = round((male_present / male_total) * 100, 2) if male_total else 0
    male_absent_pct = round((male_absent / male_total) * 100, 2) if male_total else 0
    male_sick_pct = round((male_sick / male_total) * 100, 2) if male_total else 0

    female_present = attendance_qs.filter(student__in=female_students, status="present").count()
    female_absent = attendance_qs.filter(student__in=female_students, status="absent").count()
    female_sick = attendance_qs.filter(student__in=female_students, status="sick").count()

    female_total = female_present + female_absent + female_sick
    female_present_pct = round((female_present / female_total) * 100, 2) if female_total else 0
    female_absent_pct = round((female_absent / female_total) * 100, 2) if female_total else 0
    female_sick_pct = round((female_sick / female_total) * 100, 2) if female_total else 0

    # =================== CONTEXT ===================
    context = {
        "classroom": classroom,
        "stream": stream,
        "teacher": teacher,
        "attendance_records": attendance_records,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "today": timezone.localdate(),

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
    try:
        teacher = get_object_or_404(TeacherProfile, user=request.user)

        classroom = teacher.classroom
        stream = teacher.stream
        search = request.GET.get("search", "")

        active_year = AcademicYear.objects.filter(is_active=True).first()

        students_qs = get_students_by_teacher_scope(
            classroom=classroom,
            stream=stream,
            academic_year=active_year
        ).select_related("user").prefetch_related(
            "enrollments__classroom",
            "enrollments__stream",
            "enrollments__academic_year"
        )

        if search:
            students_qs = students_qs.filter(
                Q(admission_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        students_qs = students_qs.order_by("user__first_name")

        students_list = []
        for student in students_qs:
            enrollment = student.enrollments.filter(academic_year=active_year).first()
            students_list.append({
                'id': student.id,
                'admission_number': student.admission_number,
                'full_name': student.user.get_full_name(),
                'classroom': enrollment.classroom.name if enrollment and enrollment.classroom else '—',
                'stream': enrollment.stream.name if enrollment and enrollment.stream else '—',
                'academic_year': str(enrollment.academic_year) if enrollment and enrollment.academic_year else '—',
                'gender': student.user.gender or '—',
                'phone': student.parents.first().user.phone_number if student.parents.exists() else '—',
            })

        paginator = Paginator(students_list, 25)  # 25 per page
        page_number = request.GET.get("page")
        students = paginator.get_page(page_number)

        context = {
            "students": students,
            "classroom": classroom,
            'teacher': teacher,
            "search": search,
            "active_year": active_year
        }
        return render(request, "attendance_app/my_students.html", context)

    except Exception as e:
        logger.error(f"Error in my_students: {e}")
        messages.error(request, "Unable to load students at this time. Please try again.")
        return redirect('teacher_dashboard')




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
    active_year = AcademicYear.objects.filter(is_active=True).first()

    students = get_students_by_teacher_scope(
        classroom=teacher.classroom,
        stream=teacher.stream,
        academic_year=active_year
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
    active_year = AcademicYear.objects.filter(is_active=True).first()

    students = get_students_by_teacher_scope(
        classroom=teacher.classroom,
        stream=teacher.stream,
        academic_year=active_year
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
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    profile_success = None
    password_success = None

    if request.method == "POST":
        # Update profile
        if "update_profile" in request.POST:
            user = request.user  # User instance

            # --- Update User fields ---
            user.first_name = request.POST.get("first_name", user.first_name)
            user.last_name = request.POST.get("last_name", user.last_name)
            user.username = request.POST.get("username", user.username)
            user.email = request.POST.get("email", user.email)
            user.phone_number = request.POST.get("phone_number", user.phone_number)
            user.save()

            # --- Update TeacherProfile fields ---
            if "profile_picture" in request.FILES:
                teacher_profile.profile_picture = request.FILES["profile_picture"]
            teacher_profile.classroom_id = request.POST.get(
                "classroom", teacher_profile.classroom_id
            )
            teacher_profile.stream_id = request.POST.get(
                "stream", teacher_profile.stream_id
            )
            teacher_profile.save()

            profile_success = "Profile updated successfully!"

        # Change password
        elif "change_password" in request.POST:
            old_password = request.POST.get("old_password")
            new_password1 = request.POST.get("new_password1")
            new_password2 = request.POST.get("new_password2")

            if request.user.check_password(old_password):
                if new_password1 == new_password2:
                    request.user.set_password(new_password1)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    password_success = "Password changed successfully!"
                else:
                    password_success = "New passwords do not match!"
            else:
                password_success = "Old password is incorrect!"

    context = {
        "teacher": teacher_profile,
        "profile_success": profile_success,
        "password_success": password_success,
    }
    return render(request, "attendance_app/teacher_profile.html", context)



@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def resend_sms(request, sms_id):
    try:
        teacher = request.user.teacher_profile
    except TeacherProfile.DoesNotExist:
        messages.error(request, "Teacher profile not found. Contact admin.")
        return redirect('teacher_dashboard')

    classroom = teacher.classroom
    stream = teacher.stream
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_in_class = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    sms_log = get_object_or_404(SMSLog, id=sms_id, student__in=students_in_class)

    # ✅ VALIDATION: Check parent phone number
    if not sms_log.parent or not sms_log.parent.user.phone_number:
        messages.error(request, f"Parent phone number missing for {sms_log.student.user.get_full_name()}.")
        return redirect('teacher_sms_logs')

    if not sms_log.message or sms_log.message.strip() == "":
        messages.error(request, "SMS message is empty. Cannot resend.")
        return redirect('teacher_sms_logs')

    try:
        # ✅ USE UTILITY FUNCTION
        parent_phone = sms_log.parent.user.phone_number
        sms_sent = send_sms(parent_phone, sms_log.message)

        if sms_sent:
            # ✅ UPDATE SMS LOG - SENT
            sms_log.status = "sent"
            sms_log.timestamp = timezone.now()
            sms_log.save()
            logger.info(f"SMS resent for {sms_log.student.user.get_full_name()} to {parent_phone}")
            messages.success(request, "SMS resent successfully!")
        else:
            # ✅ UPDATE SMS LOG - FAILED
            sms_log.status = "failed"
            sms_log.save()
            logger.warning(f"SMS resend failed for {sms_log.student.user.get_full_name()} to {parent_phone}")
            messages.error(request, "Failed to send SMS. Please try again.")

    except Exception as e:
        logger.error(f"Resend SMS exception for log {sms_id}: {e}")
        sms_log.status = "failed"
        sms_log.save()
        messages.error(request, f"Error: {str(e)[:80]}")

    return redirect('teacher_sms_logs')


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'teacher')
def edit_sms_log(request, sms_id):
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    classroom = teacher.classroom
    stream = teacher.stream
    active_year = AcademicYear.objects.filter(is_active=True).first()
    students_in_class = get_students_by_teacher_scope(classroom, stream, academic_year=active_year)

    sms_log = get_object_or_404(SMSLog, id=sms_id, student__in=students_in_class)

    if request.method == 'POST':
        new_message = request.POST.get('message', sms_log.message).strip()
        new_status = request.POST.get('status', sms_log.status)

        if new_status not in ['sent', 'failed', 'pending']:
            messages.error(request, 'Invalid SMS status.')
            return redirect('teacher_sms_logs')

        sms_log.message = new_message
        sms_log.status = new_status
        sms_log.save()
        messages.success(request, 'SMS log updated successfully.')
        return redirect('teacher_sms_logs')

    return render(request, 'attendance_app/edit_sms_log.html', {
        'sms_log': sms_log
    })


@never_cache
@login_required
@user_passes_test(lambda u: u.role == 'admin')
def admin_profile(request):

    if request.method == 'POST':
        # PROFILE UPDATE
        if 'update_profile' in request.POST:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()

            # Update user model
            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.username = username
            user.save()

            messages.success(request, "Profile updated successfully!")
            return redirect('admin_profile')

        # PASSWORD CHANGE
        elif 'change_password' in request.POST:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not request.user.check_password(old_password):
                messages.error(request, "Old password is incorrect.")
            elif new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
            else:
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)  # prevent logout
                messages.success(request, "Password changed successfully!")
            return redirect('admin_profile')

    context = {
    }
    return render(request, 'attendance_app/admin_profile.html', context)




from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from .models import SchoolSettings
from .forms import SchoolSettingsForm


@never_cache
@login_required
def school_settings(request):
    try:
        # Get or create settings safely
        school_settings, _ = SchoolSettings.objects.get_or_create(
            id=1,
            defaults={"school_name": "My School"}  # avoid blank error
        )

        form = SchoolSettingsForm(
            request.POST or None,
            request.FILES or None,
            instance=school_settings
        )

        if request.method == 'POST':
            if form.is_valid():
                try:
                    # Delete old logo safely
                    if 'logo' in request.FILES and school_settings.logo:
                        if default_storage.exists(school_settings.logo.name):
                            default_storage.delete(school_settings.logo.name)

                    form.save()

                    messages.success(request, "School settings updated successfully")
                    return redirect('school_settings')

                except Exception as e:
                    # Catch upload (Cloudinary) errors
                    messages.error(request, f"Upload failed: {str(e)}")

            else:
                messages.error(request, "Failed to update school settings")
                print(form.errors)  # debugging

    except Exception as e:
        # Catch unexpected system errors
        messages.error(request, f"System error: {str(e)}")
        form = None
        school_settings = None

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
    try:
        classroom = get_object_or_404(Classroom, id=classroom_id)
        streams = Stream.objects.filter(classroom=classroom)

        selected_stream_id = request.GET.get("stream")
        raw_date = request.GET.get("date")

        try:
            selected_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else now().date()
        except ValueError:
            selected_date = now().date()

        attendance_qs = Attendance.objects.filter(classroom=classroom, date=selected_date)

        if selected_stream_id:
            attendance_qs = attendance_qs.filter(stream_id=selected_stream_id)

        attendance_qs = attendance_qs.select_related("student__user", "marked_by__user").order_by("student__user__first_name")

        context = {
            "classroom": classroom,
            "attendance_records": attendance_qs,
            "streams": streams,
            "selected_date": selected_date.strftime("%Y-%m-%d"),
            "selected_stream_id": int(selected_stream_id) if selected_stream_id else None
        }

        return render(request, "attendance_app/view_class_attendance.html", context)

    except Exception as e:
        logger.error(f"Error in view_class_attendance for class {classroom_id}: {e}")
        messages.error(request, "Could not load attendance data. Please try again or contact support.")
        return redirect('attendance_report_cards')


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
        
from django.db import transaction


from django.db.models import ProtectedError
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Define promotion mapping (Badilisha majina haya yafanane na database yako)
# utils.py
CLASS_PROMOTION = {
    'Form I': 'Form II',
    'Form II': 'Form III',
    'Form III': 'Form IV',
    'Form IV': None  # Graduating students
}

def archive_attendance_for_year(year):
    """Archives attendance records to history table before starting new year"""
    from .models import Attendance, ClassAttendanceHistory
    attendances = Attendance.objects.select_related(
        'student', 'student__classroom', 'student__stream', 'marked_by'
    ).filter(student__academic_year=year)

    history_objects = []
    for att in attendances:
        history_objects.append(
            ClassAttendanceHistory(
                student=att.student,
                classroom=att.student.classroom,
                stream=att.student.stream,
                academic_year=att.student.academic_year,
                date=att.date,
                status=att.status,
                marked_by=att.marked_by
            )
        )

    ClassAttendanceHistory.objects.bulk_create(
        history_objects,
        ignore_conflicts=True
    )

@transaction.atomic
def generate_academic_year(request):
    """Generate new academic year with proper promotion logic"""
    
    last_year = AcademicYear.objects.order_by('-year_start').first()
    current_date = timezone.now()
    
    # Validation checks
    if last_year and last_year.year_start >= current_date.year + 1:
        messages.error(request, "Cannot generate beyond the near future.")
        return redirect('academic_years')
    
    if last_year and last_year.is_active and not last_year.is_locked:
        messages.error(request, "Please lock the current academic year before generating a new one.")
        return redirect('academic_years')
    
    new_start = last_year.year_start + 1 if last_year else current_date.year
    new_end = new_start + 1
    
    if AcademicYear.objects.filter(year_start=new_start).exists():
        messages.error(request, f"Academic Year {new_start}/{new_end} already exists.")
        return redirect('academic_years')
    
    try:
        with transaction.atomic():
            old_year = AcademicYear.objects.filter(is_active=True).first()
            
            # 1️⃣ ARCHIVE & LOCK OLD YEAR
            if old_year:
                archive_attendance_for_year(old_year)
                old_year.is_active = False
                old_year.is_locked = True
                old_year.save()
            
            # 2️⃣ CREATE NEW ACADEMIC YEAR
            new_year = AcademicYear.objects.create(
                year_start=new_start,
                year_end=new_end,
                is_active=True,
                is_locked=False
            )
            
            # 3️⃣ CREATE NEW CLASSROOMS & STREAMS FOR NEW YEAR
            # Hii inahakikisha data za zamani zinabaki na madarasa yake (Archives)
            if old_year:
                existing_classes = set()
                for old_class in Classroom.objects.filter(year=old_year):
                    new_class_obj, _ = Classroom.objects.get_or_create(
                        name=old_class.name,
                        year=new_year
                    )
                    existing_classes.add(old_class.name)
                    # Create streams for this new class
                    for old_stream in Stream.objects.filter(classroom=old_class):
                        Stream.objects.get_or_create(
                            name=old_stream.name,
                            classroom=new_class_obj
                        )
                
                # Create promoted classrooms if they don't exist
                for old_class in Classroom.objects.filter(year=old_year):
                    next_class_name = CLASS_PROMOTION.get(old_class.name)
                    if next_class_name and next_class_name not in existing_classes:
                        promoted_class, _ = Classroom.objects.get_or_create(
                            name=next_class_name,
                            year=new_year
                        )
                        existing_classes.add(next_class_name)
                        # Create streams for promoted class (copy from old if possible, or default)
                        # For simplicity, create a default stream or copy
                        for old_stream in Stream.objects.filter(classroom=old_class):
                            Stream.objects.get_or_create(
                                name=old_stream.name,
                                classroom=promoted_class
                            )

            # 4️⃣ PROMOTE STUDENTS
            students_promoted = 0
            students_graduated = 0
            students_skipped = 0
            
            if old_year:
                active_students = StudentProfile.objects.filter(academic_year=old_year, status='Active')
                for student in active_students:
                    try:
                        if not student.classroom:
                            students_skipped += 1
                            continue
                        
                        next_class_name = CLASS_PROMOTION.get(student.classroom.name)
                        
                        # Handle Graduation
                        if next_class_name is None:
                            student.status = 'Graduated'
                            student.save()
                            students_graduated += 1
                            continue
                        
                        # Find the target classroom in the NEW year
                        target_class = Classroom.objects.filter(name=next_class_name, year=new_year).first()
                        
                        if target_class:
                            # Find target stream
                            target_stream = None
                            if student.stream:
                                target_stream = Stream.objects.filter(name=student.stream.name, classroom=target_class).first()
                            
                            # Create new profile record for the new year
                            StudentProfile.objects.create(
                                user=student.user,
                                academic_year=new_year,
                                classroom=target_class,
                                stream=target_stream,
                                date_of_birth=student.date_of_birth,
                                admission_number=student.admission_number,
                                status='Active'
                            )
                            
                            # Mark old record as Promoted
                            student.status = 'Promoted'
                            student.save()
                            students_promoted += 1
                        else:
                            students_skipped += 1
                            
                    except Exception as e:
                        logger.error(f"Error promoting student {student.id}: {e}")
                        students_skipped += 1

            # 5️⃣ PROMOTE TEACHERS (Move them to the next class too)
            teachers_updated = 0
            for teacher in TeacherProfile.objects.all():
                if teacher.classroom:
                    # Logic: Teacher moves with students (e.g. from Form 1 to Form 2)
                    next_class_for_teacher = CLASS_PROMOTION.get(teacher.classroom.name)
                    
                    if next_class_for_teacher:
                        new_teacher_class = Classroom.objects.filter(name=next_class_for_teacher, year=new_year).first()
                        if new_teacher_class:
                            teacher.classroom = new_teacher_class
                            # Match stream
                            if teacher.stream:
                                teacher.stream = Stream.objects.filter(name=teacher.stream.name, classroom=new_teacher_class).first()
                            teacher.save()
                            teachers_updated += 1

            # Success Feedback
            msg = f"Year {new_year} Generated. Promoted: {students_promoted}, Graduated: {students_graduated}, Teachers Moved: {teachers_updated}"
            messages.success(request, msg)
            return redirect('academic_years')

    except Exception as e:
        logger.error(f"Critical error during year generation: {e}")
        messages.error(request, f"System Error: {str(e)}")
        return redirect('academic_years')

@never_cache
@login_required
def academic_year_summary(request):
    try:
        years = AcademicYear.objects.all().order_by('-year_start')
        active_year_id = request.GET.get('year')
        active_year = None
        summary_data = []

        if active_year_id:
            try:
                active_year = AcademicYear.objects.get(id=active_year_id)
            except AcademicYear.DoesNotExist:
                logger.warning(f"Academic year with ID {active_year_id} not found")
                active_year = None
            except Exception as e:
                logger.error(f"Error fetching academic year: {e}")
                messages.error(request, "Error fetching academic year.")
                active_year = None

        if active_year:
            try:
                classrooms = Classroom.objects.filter(year=active_year)
                
                for classroom in classrooms:
                    try:
                        # Get students enrolled in this classroom for the active year
                        students = StudentProfile.objects.filter(
                            enrollments__classroom=classroom,
                            enrollments__academic_year=active_year
                        ).distinct()
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
                        
                    except Exception as e:
                        logger.error(f"Error processing classroom {classroom.id}: {e}")
                        messages.warning(request, f"Error loading data for {classroom.name}. Skipping...")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching classrooms for year {active_year.id}: {e}")
                messages.error(request, "Error fetching classrooms. Please try again.")
                summary_data = []

        context = {
            'years': years,
            'active_year': active_year,
            'summary_data': summary_data,
        }

        return render(request, 'attendance_app/academic_year_summary.html', context)
        
    except Exception as e:
        logger.critical(f"Critical error in academic_year_summary: {e}")
        messages.error(request, "A critical error occurred. Please try again later.")
        return redirect('academic_years')




