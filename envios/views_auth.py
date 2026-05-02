from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .models import Empleado


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(
                    request,
                    f'Bienvenido, {user.get_full_name() or user.username}!',
                )
                next_page = request.POST.get('next') or request.GET.get('next') or 'dashboard'
                return redirect(next_page)
            messages.error(request, 'Usuario o contrasena incorrectos.')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': request.GET.get('next', '')})


def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesion correctamente.')
    return redirect('login')


@login_required
def perfil_view(request):
    empleado = Empleado.objects.filter(email=request.user.email).first()
    return render(request, 'accounts/perfil.html', {'empleado': empleado})
