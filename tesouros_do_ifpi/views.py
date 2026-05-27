from django.http import HttpResponse
from openpyxl import Workbook
from django.shortcuts import render, redirect
from .models import Contato, Usuario, Voto, Foto, Categoria
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ExAluno, AlunoAtual, DocenteAtual, ExDocente, TecnicoAdmAtual, ExTecnicoAdm, Terceirizado
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count
from django.core.paginator import Paginator
from .utils import validar_cpf, formatar_cpf, limpar_cpf
from django.contrib.auth import get_user_model
import logging
User = get_user_model()

FORM_CATEGORIAS = {

    "ex-aluno-do-ifpi": ExAluno,
    "aluno-atual-do-ifpi": AlunoAtual,
    "professor-atual-do-ifpi": DocenteAtual,
    "ex-professor-do-ifpi": ExDocente,
    "tecnico-atual-do-ifpi": TecnicoAdmAtual,
    "ex-tecnico-do-ifpi": ExTecnicoAdm,
    "terceirizado": Terceirizado,

}

def contato(request):
    if request.method == "POST":
        # Captura os dados do formulário
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        assunto = request.POST.get('assunto')
        telefone = request.POST.get('telefone')
        mensagem = request.POST.get('mensagem')
        
        # Cria um novo contato no banco de dados
        contato = Contato(nome=nome, email=email, assunto=assunto, telefone=telefone, mensagem=mensagem)
        contato.save()

        # Mensagem de sucesso
        messages.success(request, "Mensagem enviada com sucesso!")
        
        # Redireciona para a mesma página ou para uma página de sucesso
        return redirect('contato')  # Aqui, você pode mudar o redirecionamento para outra página de sucesso

    return render(request, 'user/contato.html')

def home_contato(request):

    if request.method == "POST":

        nome = request.POST.get("name")
        email = request.POST.get("email")
        telefone = request.POST.get("phone")        
        mensagem = request.POST.get("message")

        Contato.objects.create(
            nome=nome,
            email=email,
            telefone=telefone,            
            mensagem=mensagem
        )

        messages.success(request, "Mensagem enviada com sucesso!")
        return redirect('index')

    return redirect('index')

# def termos(request):

#     if not request.session.get('cpf_autorizado'):
#         return redirect('identificacao')
    
#     if request.method == "POST":

#         concorda_termos = request.POST.get('concorda_termos') == 'on'
#         cpf = request.session.get('cpf_autorizado')

#         if concorda_termos and cpf:

#             usuario = get_object_or_404(Usuario, cpf=cpf)

#             usuario.concorda_termos = True
#             usuario.data_aceite = timezone.now()
#             ip = request.META.get('REMOTE_ADDR')
#             usuario.ip_aceite = ip

#             usuario.save()

#             return redirect('votacao')

#         else:
#             messages.error(request, "Você deve concordar com os termos para continuar.")
#             return redirect('termos')

#     return render(request, 'termos.html')


@login_required(login_url='identificacao')
def termos(request):

    usuario = request.user

    # Se já aceitou, não precisa ver de novo
    if usuario.concorda_termos:
        return redirect('votacao')

    if request.method == "POST":
        concorda_termos = request.POST.get('concorda_termos') == 'on'

        if concorda_termos:
            usuario.concorda_termos = True
            usuario.data_aceite = timezone.now()

            # Captura IP
            ip = request.META.get('REMOTE_ADDR')
            usuario.ip_aceite = ip

            usuario.save()

            return redirect('votacao')
        else:
            messages.error(request, "Você deve concordar com os termos para continuar.")
            return redirect('termos')

    return render(request, 'user/termos.html')



def identificacao(request):

    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect("dashboard")
        return redirect("votacao")

    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("password")

        user = authenticate(request, username=email, password=senha)

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect("dashboard")
            else:
                return redirect("votacao")

        else:
            messages.error(request, "Email ou senha inválidos.")

    return render(request, "user/identificacao.html")



def sair(request):
    logout(request)
    return redirect('index')


# def meus_votos(request):
#     cpf = request.session.get('cpf_autorizado')

#     if not cpf:
#         return redirect('identificacao')

#     usuario = get_object_or_404(Usuario, cpf=cpf)

#     if usuario.concorda_termos == False:
#         return redirect('termos')
    
#     votos = Voto.objects.filter(usuario=usuario)

#     return render(request, 'meus_votos.html', {'votos': votos})

@login_required(login_url='identificacao')
def meus_votos(request):
    usuario = request.user

    if not usuario.concorda_termos:
        return redirect('termos')
    
    votos = Voto.objects.filter(usuario=usuario)

    return render(request, 'user/meus_votos.html', {'votos': votos, 'usuario': usuario })


# def votar(request, voto_id):

#     cpf = request.session.get('cpf_autorizado')

#     if not cpf:
#         return redirect('identificacao')

#     usuario = get_object_or_404(Usuario, cpf=cpf)

#     voto = get_object_or_404(Voto, id=voto_id, usuario=usuario)
    
#     if usuario.concorda_termos == False:
#         return redirect('termos')

#     if voto.confirmacao:
#         return redirect('votacao')

#     FormClass = FORM_CATEGORIAS.get(voto.categoria.slug)

#     if not FormClass:
#         return redirect('votacao')

#     if request.method == "POST":

#         form = FormClass(request.POST, instance=voto)

#         if form.is_valid():

#             voto = form.save(commit=False)
#             voto.confirmacao = True
#             voto.data_confirmacao = timezone.now()
#             voto.save()

#             return redirect('votacao')

#     else:

#         form = FormClass(instance=voto)

#     return render(request, "votar.html", {
#         "form": form,
#         "voto": voto
#     })


@login_required(login_url='identificacao')
def votar(request, uuid):

    usuario = request.user

    # Verifica se aceitou os termos
    if not usuario.concorda_termos:
        return redirect('termos')

    voto = get_object_or_404(Voto, uuid=uuid, usuario=usuario)

    # Evita votar duas vezes
    if voto.confirmacao:
        return redirect('votacao')

    FormClass = FORM_CATEGORIAS.get(voto.categoria.slug)

    if not FormClass:
        return redirect('votacao')

    if request.method == "POST":
        form = FormClass(request.POST, instance=voto)

        if form.is_valid():
            voto = form.save(commit=False)
            voto.confirmacao = True
            voto.data_confirmacao = timezone.now()
            voto.save()

            return redirect('votacao')

    else:
        form = FormClass(instance=voto)

    return render(request, "user/votar.html", {
        "form": form,
        "voto": voto
    })
logger = logging.getLogger(__name__)
def index(request):
    try:
        # Busca apenas as fotos ativas, ordenando das mais recentes para as mais antigas
        fotos = Foto.objects.filter(ativo=True).order_by('-criado_em')
    except Exception as e:
        # Registra o erro no log do servidor com detalhes
        logger.error(f"Erro ao buscar fotos no banco de dados: {e}")
        fotos = Foto.objects.none()  # Retorna um QuerySet vazio seguro em vez de uma lista []

    context = {
        "fotos": fotos
    }
    
    return render(request, 'index.html', context)

def nao_autorizado(request):
    return render(request, 'user/nao_autorizado.html')

### Views administrativas


@login_required
def dashboard(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')
    
    qtde_usuarios = Usuario.objects.count()
    qtde_usuarios_concordaram = Usuario.objects.filter(concorda_termos=True).count()
    qtde_usuarios_n_concordaram = Usuario.objects.filter(concorda_termos=False).count()
    qtde_contatos = Contato.objects.count()
    qtde_votos = Voto.objects.count()
    qtde_fotos = Foto.objects.count()
    qtde_categorias = Categoria.objects.count()
    qtde_votos_confirmados = Voto.objects.filter(confirmacao=True).count()
    
    

    
    
    return render(request, 'admin/dashboard.html', {
        "qtde_usuarios": qtde_usuarios,
        "qtde_usuarios_concordaram": qtde_usuarios_concordaram,
        "qtde_usuarios_n_concordaram": qtde_usuarios_n_concordaram,
        "qtde_contatos": qtde_contatos,
        "qtde_votos": qtde_votos,
        "qtde_fotos": qtde_fotos,
        "qtde_categorias": qtde_categorias,
        "qtde_votos_confirmados": qtde_votos_confirmados
    })

@login_required
def listar_categorias(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')
    
    categorias = Categoria.objects.all()
    return render(request, 'admin/categorias.html', {'categorias': categorias})

@login_required
def editar_categoria(request, id):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    categoria = get_object_or_404(Categoria, id=id)

    if request.method == 'POST':
        categoria.nome = request.POST.get('nome')
        categoria.descricao = request.POST.get('descricao')
        categoria.save()

    return redirect('categorias')

@login_required
def listar_contatos(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')
    
    contatos = Contato.objects.all().order_by('-data')
    paginator = Paginator(contatos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/contatos.html', {'contatos': page_obj})

@login_required
def listar_votos(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    votos_por_categoria = (
        Voto.objects
        .filter(confirmacao=True)
        .values('categoria__id', 'categoria__nome', 'categoria__slug')
        .annotate(total=Count('id'))
        
    )

    return render(request, 'admin/votos.html', {
        'votos_por_categoria': votos_por_categoria
    })
    
@login_required
def relatorio_categoria(request, slug):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    categoria = get_object_or_404(Categoria, slug=slug)

    votos = (
        Voto.objects
        .filter(categoria=categoria, confirmacao=True)
        .order_by('nome')
    )

    return render(request, 'admin/relatorio_categoria.html', {
        'categoria': categoria,
        'votos': votos
    })
    
    
@login_required
def exportar_excel_categoria(request, slug):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    categoria = get_object_or_404(Categoria, slug=slug)

    votos = Voto.objects.filter(
        categoria=categoria,
        confirmacao=True
    ).order_by('nome')

    # Criar planilha
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatório"

    # Cabeçalhos
    ws.append([
        "Nome",
        "Curso",
        "Setor",
        "Função",
        "Empresa",
        "Ocupação Atual",
        "Data do Voto"
    ])

    # Dados
    for voto in votos:
        ws.append([
            voto.nome,
            voto.nome_curso,
            voto.nome_setor,
            voto.nome_funcao,
            voto.nome_empresa,
            voto.nome_ou_ocupacao_atual,
            voto.data_voto.strftime('%d/%m/%Y %H:%M') if voto.data_voto else ''
        ])

    # Resposta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=relatorio_{categoria.slug}.xlsx'

    wb.save(response)
    return response
    
@login_required
def listar_fotos(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    fotos_lista = Foto.objects.all().order_by('-criado_em')

    paginator = Paginator(fotos_lista, 9)  
    page_number = request.GET.get('page')
    fotos = paginator.get_page(page_number)

    return render(request, 'admin/fotos.html', {'fotos': fotos})

@login_required
def criar_foto(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    if request.method == 'POST':
        nome = request.POST.get('nome')
        imagem = request.FILES.get('imagem')
        descricao = request.POST.get('descricao')
        link = request.POST.get('link')
        ativo = True if request.POST.get('ativo') else False

        Foto.objects.create(
            nome=nome,
            imagem=imagem,
            descricao=descricao,
            link=link,
            ativo=ativo
        )

    return redirect('fotos')


@login_required
def editar_foto(request, id):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    foto = get_object_or_404(Foto, id=id)

    if request.method == 'POST':
        foto.nome = request.POST.get('nome')
        foto.descricao = request.POST.get('descricao')
        foto.link = request.POST.get('link')
        foto.ativo = True if request.POST.get('ativo') == 'on' else False

        # Atualiza imagem se enviou nova
        if request.FILES.get('imagem'):
            foto.imagem = request.FILES.get('imagem')

        foto.save()
        return redirect('fotos')

    return redirect('fotos')

@login_required
def toggle_foto(request, id):
    """Ativar / Desativar"""
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    foto = get_object_or_404(Foto, id=id)
    foto.ativo = not foto.ativo
    foto.save()

    return redirect('fotos')

@login_required
def excluir_foto(request, id):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    foto = get_object_or_404(Foto, id=id)
    foto.delete()

    return redirect('fotos')

@login_required
def listar_usuarios(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')
    
    usuarios = Usuario.objects.all()
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/usuarios.html', {'usuarios': page_obj})

@login_required
def criar_usuario(request):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    if request.method == 'POST':
        email = request.POST.get('email')
        cpf = request.POST.get('cpf')

        cpf_limpo = limpar_cpf(cpf)

        
        if not validar_cpf(cpf_limpo):
            messages.error(request, "CPF inválido.")
            return redirect('usuarios')  

        cpf_formatado = formatar_cpf(cpf_limpo)

        
        if User.objects.filter(cpf=cpf_formatado).exists():
            messages.error(request, "CPF já cadastrado.")
            return redirect('usuarios')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email já cadastrado.")
            return redirect('usuarios')

        
        user = User.objects.create_user(
            username=email,
            email=email,
            cpf=cpf_formatado
        )

        
        user.set_password(cpf_limpo)
        user.save()

        messages.success(request, "Usuário criado com sucesso!")

    return redirect('usuarios')


@login_required
def apagar_usuario(request, id):
    if not request.user.is_superuser:
        return redirect('nao_autorizado')

    usuario = get_object_or_404(User, id=id)

    # Evita o admin apagar a si mesmo
    if usuario == request.user:
        messages.error(request, "Você não pode apagar seu próprio usuário.")
        return redirect('usuarios')

    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuário excluído com sucesso!")

    return redirect('usuarios')