from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='группа для теста',
            slug='test_slug',
        )
        cls.user = User.objects.create(
            username='user_test'
        )
        cls.post = Post.objects.create(
            text='текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):

        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.url_only_authorized = ('/create/', '/posts/1/edit/',)
        self.url_non_existent = ('/non_existent_page/',)
        self.url_full_list = (
            '/',
            '/group/test_slug/',
            '/create/',
            '/posts/1/',
            '/posts/1/edit/',
            '/profile/user_test/',
            '/non_existent_page/',
        )

    def test_url_for_guest(self):
        """Тест: проверка доступности страниц для гостя """
        for i_adress in self.url_full_list:
            with self.subTest(adress=i_adress):
                response = self.guest_client.get(i_adress)

                if i_adress in self.url_only_authorized:
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.FOUND,
                        f'Для гостя страница {i_adress} недоступена'
                    )
                elif i_adress in self.url_non_existent:
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.NOT_FOUND,
                        f'Для гостя проверка доступа к '
                        f'несуществующей странице {i_adress} провалена'
                    )
                else:
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.OK,
                        f'Для гостя страница {i_adress} недоступена'
                    )

    def test_url_for_authorized(self):
        """Тест: проверка доступности страниц для авторизованного """
        for i_adress in self.url_full_list:
            with self.subTest(adress=i_adress):
                response = self.authorized_client.get(i_adress)
                if i_adress in self.url_non_existent:
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.NOT_FOUND,
                        f'Для авторизованного проверка доступа к'
                        f' несуществующей странице {i_adress} провалена'
                    )
                else:
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.OK,
                        f'Для авторизованного страница {i_adress} недоступена'
                    )

    def test_authorized_redirects(self):
        """Тест: редиректа у авторизованного пользователя — не автора"""
        user_not_author = User.objects.create(username='user_not_author')
        authorized_client_not_author = Client()
        authorized_client_not_author.force_login(user_not_author)
        response = authorized_client_not_author.get(
            '/posts/1/edit/',
            follow=True
        )
        self.assertRedirects(response, '/posts/1/')

    def test_guest_redirects(self):
        """Тест: редиректа у гостя"""
        url = '/posts/1/edit/'
        response = self.guest_client.get(
            url,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=' + url)

    def test_url_template_app_posts(self):
        """Тест: URL-адреса и шаблона."""
        templates_url = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/posts/1/edit/': 'posts/post_create.html',
            '/posts/1/': 'posts/post_detail.html',
            '/profile/user_test/': 'posts/profile.html',
            '/create/': 'posts/post_create.html',
        }
        for i_adress, i_template in templates_url.items():
            with self.subTest(adress=i_adress):
                if i_adress in self.url_only_authorized:
                    response = self.authorized_client.get(i_adress)
                    self.assertTemplateUsed(
                        response,
                        i_template,
                        f'Для авторизованного пользователя по адресу'
                        f' {i_adress} в шаблоне {i_template} ошибка.'
                    )
                else:
                    response = self.guest_client.get(i_adress)
                    self.assertTemplateUsed(
                        response,
                        i_template,
                        f'Для гостя по адресу {i_adress} '
                        f'в шаблоне {i_template} ошибка.'
                    )

    def test_404_page(self):
            """Проверка 404 для несуществующих страниц."""
            url = '/unexisting_page/'
            authorized_client_not_author = Client()
            clients = (
                self.authorized_client,
                self.client,
                authorized_client_not_author
            )
            for role in clients:
                with self.subTest(url=url):
                    response = role.get(url, follow=True)
                    self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                    self.assertTemplateUsed(response, 'core/404.html')

from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from django.urls import reverse

from ..models import Comment, Group, Post


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='auth')
        cls.user_author_following = (
            User.objects.create_user(username='following')
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовая пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user_author,
            text='Тестовый комментарий',
        )
        cls.pages_names_urls = (
            ('posts:index', None, '/'),
            ('posts:group_list', (cls.group.slug,), '/group/test-slug/'),
            ('posts:profile', (cls.post.author.username,), '/profile/auth/'),
            ('posts:post_detail', (cls.post.id,), '/posts/1/'),
            ('posts:post_edit', (cls.post.id,), '/posts/1/edit/'),
            ('posts:post_create', None, '/create/'),
            ('posts:add_comment', (cls.post.id,), '/posts/1/comment/'),
            ('posts:follow_index', None, '/follow/'),
            ('posts:profile_follow',
                (cls.user_author.username,),
                '/profile/auth/follow/'),
            ('posts:profile_unfollow',
                (cls.user_author.username,),
                '/profile/auth/unfollow/'),
        )

    def setUp(self):
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)

        self.user_not_author = User.objects.create_user(username='HasNoName')
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user_not_author)

    def test_pages_use_correct_template(self):
        """Проверка использования правильного шаблона."""
        pages_names_templates = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_list', (self.group.slug,), 'posts/group_list.html'),
            ('posts:profile', (self.post.author.username,),
             'posts/profile.html'),
            ('posts:post_detail', (self.post.id,), 'posts/post_detail.html'),
            ('posts:post_edit', (self.post.id,), 'posts/post_create.html'),
            ('posts:post_create', None, 'posts/post_create.html'),
            ('posts:follow_index', None, 'posts/follow.html'),
        )
        for name, arg, template in pages_names_templates:
            with self.subTest(name=name):
                response = (
                    self.authorized_client_author
                    .get(reverse(name, args=arg))
                )
                self.assertTemplateUsed(response, template)

    def test_urls_equals_reverse_names(self):
        """URL адреса равны адресам, полученным по reverse(name)."""
        for name, arg, url in self.pages_names_urls:
            with self.subTest(name=name):
                self.assertEqual(reverse(name, args=arg), url)

    def test_unexisting_page(self):
        """Запрос к несуществующей странице вернет ошибку 404"""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_url_exists_for_author(self):
        """Доступность страниц автору"""
        for name, arg, url in self.pages_names_urls:
            with self.subTest(name=name):
                response = (self.authorized_client_author
                            .get(reverse(name, args=arg)))
                if name in (
                    'posts:add_comment',
                    'posts:delete_comment',
                ):
                    self.assertRedirects(
                        response,
                        reverse('posts:post_detail', args=(self.post.id,))
                    )
                elif name in (
                    'posts:profile_follow',
                    'posts:profile_unfollow',
                    'posts:post_delete',
                ):
                    self.assertRedirects(
                        response,
                        reverse('posts:profile',
                                args=(self.user_author.username,))
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exists_for_not_author(self):
        """Доступность страниц авторизованному не автору"""
        for name, arg, url in self.pages_names_urls:
            with self.subTest(name=name):
                response = (self.authorized_client_not_author
                            .get(reverse(name, args=arg)))
                if name in (
                    'posts:post_edit',
                    'posts:add_comment',
                    'posts:post_delete',
                    'posts:edit_comment',
                    'posts:delete_comment',
                ):
                    self.assertRedirects(
                        response,
                        reverse('posts:post_detail', args=(self.post.id,))
                    )
                elif name in (
                    'posts:profile_follow',
                    'posts:profile_unfollow',
                ):
                    self.assertRedirects(
                        response,
                        reverse('posts:profile',
                                args=(self.user_author.username,))
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exists_for_not_authorized_client(self):
        """Доступность страниц анониму"""
        for name, arg, url in self.pages_names_urls:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=arg))
                if name in (
                    'posts:post_edit', 'posts:post_create',
                    'posts:add_comment', 'posts:profile_follow',
                    'posts:profile_unfollow', 'posts:follow_index',
                ):
                    reverse_login = reverse('users:login')
                    reverse_name = reverse(name, args=arg)
                    self.assertRedirects(
                        response,
                        f'{reverse_login}?next={reverse_name}'
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)
