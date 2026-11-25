from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .emails import send_otp
from .forms import LoginForm, OTPForm, PostForm, RegisterForm
from .models import EmailVerification, Post

PENDING_KEY = 'pending_user_id'  # session key for "who is verifying right now"
BACKEND = 'core.backends.EmailOrUsernameBackend'


# --- helpers ----------------------------------------------------------------

def needs_verification(user):
    """Superusers made with createsuperuser skip email verification."""
    if user.is_superuser:
        return False
    verification = EmailVerification.objects.filter(user=user).first()
    return not (verification and verification.is_verified)


def get_pending_user(request):
    user_id = request.session.get(PENDING_KEY)
    if user_id:
        return User.objects.filter(pk=user_id).first()
    if request.user.is_authenticated:
        return request.user
    return None


def mask_email(email):
    name, _, domain = email.partition('@')
    return f'{name[:1]}{"•" * max(len(name) - 1, 2)}@{domain}'


def verified_required(view):
    """Like @login_required, but also sends unverified users to the code page."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if needs_verification(request.user):
            request.session[PENDING_KEY] = request.user.pk
            return redirect('verify_email')
        return view(request, *args, **kwargs)
    return wrapper


# --- pages ------------------------------------------------------------------

def home(request):
    latest_posts = Post.objects.select_related('author')[:3]
    return render(request, 'core/home.html', {'latest_posts': latest_posts})


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_otp(user)
            request.session[PENDING_KEY] = user.pk
            messages.success(request, f'Account created. We sent a 6-digit code to {mask_email(user.email)}.')
            return redirect('verify_email')
    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})


class LoginView(auth_views.LoginView):
    template_name = 'core/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if needs_verification(user):
            # Correct password, but email not confirmed yet: send them to verify first.
            verification, _ = EmailVerification.objects.get_or_create(user=user)
            if verification.seconds_until_resend() == 0:
                send_otp(user)
            self.request.session[PENDING_KEY] = user.pk
            messages.info(self.request, 'Please verify your email to finish signing in.')
            return redirect('verify_email')
        return super().form_valid(form)


def verify_email(request):
    user = get_pending_user(request)
    if user is None:
        messages.info(request, 'Log in to verify your email.')
        return redirect('login')
    if not needs_verification(user):
        return redirect('dashboard')

    verification, _ = EmailVerification.objects.get_or_create(user=user)
    form = OTPForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        ok, error = verification.check_code(form.cleaned_data['code'])
        if ok:
            request.session.pop(PENDING_KEY, None)
            login(request, user, backend=BACKEND)
            messages.success(request, 'Email verified. Welcome!')
            return redirect('dashboard')
        form.add_error('code', error)

    return render(request, 'core/verify_email.html', {
        'form': form,
        'email': mask_email(user.email),
        'resend_wait': verification.seconds_until_resend(),
    })


@require_POST
def resend_otp(request):
    user = get_pending_user(request)
    if user is None:
        return redirect('login')

    verification, _ = EmailVerification.objects.get_or_create(user=user)
    wait = verification.seconds_until_resend()
    if wait:
        messages.warning(request, f'Please wait {wait} seconds before requesting another code.')
    else:
        send_otp(user)
        messages.success(request, f'A new code has been sent to {mask_email(user.email)}.')
    return redirect('verify_email')


@verified_required
def dashboard(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post published.')
            return redirect('dashboard')
    else:
        form = PostForm()

    posts = request.user.posts.all()
    return render(request, 'core/dashboard.html', {
        'form': form,
        'posts': posts,
        'post_count': posts.count(),
    })
