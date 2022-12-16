from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page

from .models import Post, Group, Follow
from .forms import PostForm, CommentForm

POSTS_PER_PAGE = 10
User = get_user_model()


def paginator(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    page_obj = paginator(request, post_list)
    template = 'posts/index.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = paginator(request, post_list)
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    page_obj = paginator(request, post_list)
    following = (request.user.is_authenticated and author.following.filter(
        user=request.user).exists())
    template = 'posts/profile.html'
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    """Отображает заметку с индексом <post_id>"""

    post = get_object_or_404(
        Post,
        pk=post_id
    )
    comments = post.comments.all()
    form = CommentForm()
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'form': form,
        'comments': comments,
    })

@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post_create = form.save(commit=False)
        post_create.author = request.user
        post_create.save()
        return redirect('posts:profile', post_create.author)
    template = 'posts/post_create.html'
    context = {'form': form}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post_edit = get_object_or_404(Post, id=post_id)
    if request.user != post_edit.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None, instance=post_edit)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    template = 'posts/post_create.html'
    context = {'form': form, 'is_edit': True, 'post_id': post_id}
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    """Добавляем комменатрий."""
    post = get_object_or_404(Post.objects.select_related(), id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница с постами авторов, на которых подписан текущий пользователь.
    Информация о текущем пользователе доступна в переменной request.user.
    Following - ссылка на объект пользователя, на которого подписываются.
    """
    followed_posts = Post.objects.filter(author__following__user=request.user)
    context = {'page_obj': paginator(request, followed_posts)}

    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Страница для подписки на автора с редиректом на профайл."""
    following_author = get_object_or_404(User, username=username)
    if (
        Follow.objects.filter(author=following_author,
                              user=request.user).exists()
        or request.user == following_author
    ):

        return redirect('posts:profile', username=username)

    Follow.objects.create(
        user=request.user,
        author=following_author,
    )

    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Страница для отписки от автора с редиректом на профайл."""
    author_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user,
                          author=author_to_unfollow).delete()

    return redirect('posts:profile', username=username)


@login_required
def follow_index(request):
    post_list = (
        Post.objects.filter(author__following__user=request.user).
        select_related('author', 'group')
    )
    page_obj = paginator(request, post_list)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)