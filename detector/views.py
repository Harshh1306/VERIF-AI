from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DetectionRecordUpdateForm, DetectionUploadForm, SignUpForm
from .models import DetectionRecord
from .services import predict_image, predict_video


class UserLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'detector/landing.html')


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Your account has been created successfully.')
            return redirect('dashboard')
    else:
        form = SignUpForm()

    return render(request, 'auth/signup.html', {'form': form})


def about(request):
    return render(request, 'detector/about.html')


@login_required
def dashboard(request):
    records = DetectionRecord.objects.filter(user=request.user)[:6]
    stats = {
        'total': DetectionRecord.objects.filter(user=request.user).count(),
        'images': DetectionRecord.objects.filter(user=request.user, file_type='image').count(),
        'videos': DetectionRecord.objects.filter(user=request.user, file_type='video').count(),
        'fake': DetectionRecord.objects.filter(user=request.user, result='fake').count(),
        'uncertain': DetectionRecord.objects.filter(user=request.user, result='uncertain').count(),
    }
    return render(request, 'detector/dashboard.html', {'records': records, 'stats': stats})


@login_required
def detect(request):
    analysis = None

    if request.method == 'POST':
        form = DetectionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['uploaded_file']
            file_type = form.cleaned_data['file_type']
            title = form.cleaned_data['title']

            try:
                detector = predict_image if file_type == 'image' else predict_video
                analysis = detector(uploaded_file)
                uploaded_file.seek(0)

                record = DetectionRecord.objects.create(
                    user=request.user,
                    title=title,
                    file_type=file_type,
                    uploaded_file=uploaded_file,
                    result=analysis['label'],
                    confidence=analysis['confidence'],
                    summary=analysis['summary'],
                )
                analysis['record'] = record
                messages.success(request, 'Analysis completed and saved to your dashboard.')
            except Exception as exc:
                messages.error(request, f'Analysis failed: {exc}')
    else:
        form = DetectionUploadForm()

    return render(request, 'detector/detect.html', {'form': form, 'analysis': analysis})


@login_required
def history(request):
    records = DetectionRecord.objects.filter(user=request.user)
    record_forms = [
        {
            'record': record,
            'form': DetectionRecordUpdateForm(instance=record),
        }
        for record in records
    ]
    return render(request, 'detector/history.html', {'record_forms': record_forms})


@login_required
def update_record(request, pk):
    record = get_object_or_404(DetectionRecord, pk=pk, user=request.user)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST request required.'}, status=405)

    form = DetectionRecordUpdateForm(request.POST, instance=record)
    if form.is_valid():
        saved_record = form.save()
        return JsonResponse(
            {
                'ok': True,
                'message': 'Report updated successfully.',
                'title': saved_record.title,
                'notes': saved_record.notes,
                'notes_display': saved_record.notes or 'No notes added yet.',
            }
        )

    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
def delete_record(request, pk):
    record = get_object_or_404(DetectionRecord, pk=pk, user=request.user)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST request required.'}, status=405)

    record.delete()
    return JsonResponse({'ok': True, 'message': 'Report deleted successfully.'})
