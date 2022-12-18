import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.urls import reverse
from django.conf import settings

from ..models import Group, Post, Follow
from ..const import NUM_POST, NUM_PAG

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Это название тестовой группы',
            slug='test-slug',
            description='описание группы. Тест',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post_count = Post.objects.count()
        cls.post = Post.objects.create(
            text='текст поста',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.templates_pages_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': cls.user}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}):
                'posts/post_detail.html',
        }
        cls.url_form_test = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}),
        }
        cls.page_index = reverse('posts:index')

    def setUp(self):
        cache.clear()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:post_create')))
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField}
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context_for_post_edit(self):
        """Шаблон create_post сформирован с правильным контекстом
        при редактировании поста."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField}

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        self.assertEqual(response.context['is_edit'], True)
        self.assertIsInstance(response.context['is_edit'], bool)

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(response.context['author'], self.user)
        self.check_post(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.check_post(response.context['post'])

    def test_index_list_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        response_text = response.context['page_obj'][0].text
        response_author = response.context['page_obj'][0].author
        response_group = response.context['page_obj'][0].group
        self.assertEqual(response_text, self.post.text)
        self.assertEqual(response_author.username, self.user.username)
        self.assertEqual(response_group.title, self.group.title)

    def test_post_on_the_home_page(self):
        """ Тест на появление поста на главной странице после создания """
        response = self.authorized_client.get(reverse('posts:index'))
        test_post = response.context['page_obj'].object_list[0]
        self.assertEqual(self.post, test_post, (
            "Пост не добавился на главную страницу"
        ))

    def test_post_not_belongs_to_someone_else_group(self):
        """ Тест на принадлежность поста нужной группе """
        alien_group = Group.objects.create(
            title='alien',
            slug='alien_slug',
            description='alien_desc'
        )
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': alien_group.slug}))
        alien_posts = response.context['page_obj']
        self.assertNotIn(self.post, alien_posts, (
            ' Пост принадлежит чужой группе '
        ))

    def test_profile_correct_context(self):
        """ Тест на появление поста на странице пользователя """
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user}
        ))
        test_author = response.context['author']
        posts = response.context['page_obj']
        self.assertEqual(test_author, self.user, ('Указан неверный автор '))
        self.assertIn(self.post, posts, (
            ' Пост автора не отображается на странице автора '
        ))

    def test_post_on_the_group_page(self):
        """ Тест на появление поста на странице группы после создания """
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': 'test-slug'}
        ))
        test_post = response.context['page_obj'].object_list[0]
        self.assertEqual(self.post, test_post, (
            "Пост не добавился на страницу группы"
        ))

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
                        'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
                        'posts/post_create.html',
            reverse('posts:follow'): 'posts/follow.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_uses_correct_template(self):
        """
        URL-адрес использует соответствующий шаблон.
        Шаблон сформирован с правильным контекстом.
        """
        for i_url, template in self.templates_pages_names.items():
            with self.subTest(i_url=i_url):
                response = self.authorized_client.get(i_url)
                self.assertTemplateUsed(response, template)

                if 'page_obj' in response.context:
                    self.check_post(response.context['page_obj'][0])
                if 'post' in response.context:
                    self.check_post(response.context['post'])

    def test_cache(self):
        posts_count = Post.objects.count()
        post = Post.objects.create(
            text='test text',
            author=self.user,
            group=self.group,
            image=self.uploaded
        )
        response = self.authorized_client.get(self.page_index)
        response_posts_count = len(response.context['page_obj'])
        response_content_cached = response.content
        self.assertEqual(response_posts_count, posts_count + 1)

        post.delete()
        response = self.authorized_client.get(self.page_index)
        self.assertEqual(response_content_cached, response.content)

        cache.clear()
        response = self.authorized_client.get(self.page_index)
        self.assertNotEqual(response_content_cached, response.content)


class PaginatorViewsTest(TestCase):
    """Тестируем Paginator. Страница должна быть разбита на 10 постов"""
    POSTS_COUNT = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='TestUser')
        Post.objects.bulk_create([Post(
            text=f'Тестовое сообщение{i}',
            author=cls.user)
            for i in range(cls.POSTS_COUNT)])

    def test_first_page_contains_ten_records(self):
        """Тестируем Paginator.Первые 10 постов на первой странице index"""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context.get('page_obj').object_list), NUM_POST)

    def test_second_page_contains_three_records(self):
        """Тестируем Paginator.Последние 3 поста на второй странице index"""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context.get('page_obj').object_list), NUM_PAG)


class TestFollowViews(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='user'
        )
        cls.author = User.objects.create(
            username='author'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=TestFollowViews.author
        )

        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.url_unfollow = reverse(
            'posts:profile_unfollow',
            kwargs={'username': cls.user}
        )
        cls.url_follow = reverse(
            'posts:profile_follow',
            args=[TestFollowViews.author]
        )
        cls.url_follow_index = reverse('posts:follow_index')

    def setUp(self):
        cache.clear()

    def test_auth_follow(self):
        """ Авторизованный пользователь может подписываться на других
            пользователей.
        """
        self.authorized_client.get(self.url_follow)
        follower = Follow.objects.get(author=TestFollowViews.author.id)
        self.assertEqual(TestFollowViews.user.id, follower.user.id)

    def test_auth_unfollow(self):
        """ Авторизованный пользователь может отписываться от других
            пользователей.
        """
        Follow.objects.create(user=self.user, author=self.user)
        self.authorized_client.get(self.url_unfollow)
        create_follow = Follow.objects.values_list('user', flat=True)
        self.assertNotIn(TestFollowViews.user.id, create_follow)

    def test_new_post_follow(self):
        """ Новая запись пользователя появляется в ленте тех, кто на него
            подписан.
        """
        post = Post.objects.create(
            author=self.user,
            text='Test post')
        posts_count = Post.objects.count()
        Follow.objects.create(user=self.user, author=self.user)
        response = self.authorized_client.get(self.url_follow_index)
        response_posts_count = len(response.context['page_obj'])
        self.assertEqual(posts_count, response_posts_count + 1)
        self.assertEqual(response.context['page_obj'][0].text, post.text)

    def test_new_post_unfollow(self):
        """ Новая запись пользователя не появляется в ленте тех,
            кто не подписан на него.
        """
        Post.objects.create(
            author=self.user,
            text='Test post')
        Follow.objects.create(user=self.user, author=self.user)
        response = self.authorized_client.get(self.url_follow_index)
        response_posts_count_follow = len(response.context['page_obj'])
        self.authorized_client.get(self.url_unfollow)
        response = self.authorized_client.get(self.url_follow_index)
        response_posts_count_unfollow = len(response.context['page_obj'])
        self.assertEqual(response_posts_count_follow - 1,
                         response_posts_count_unfollow)
