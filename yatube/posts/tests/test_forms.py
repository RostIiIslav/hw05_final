from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post, Comment

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(
            username='post_author',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.group_new = Group.objects.create(
            title='Тестовое название группы: Сериалы',
            slug='test_slug_new',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.post_author,
            text='Тестовый самый при самый, тестовый из тестовейших',
        )

        cls.form_comment_data = {
            'text': 'this is comment'
        }
        cls.form_data = {
            'text': 'Тестовый текст 2',
            'group': 1,
        }

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

        cls.url = {
            'create': reverse('posts:post_create'),
            'login': reverse('login'),
            'comment': reverse(
                'posts:add_comment', kwargs={'post_id': cls.post.id}),
            'post_detail': reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}),
            'post_edit': reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}),
            'group_list': reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}),
            'profile': reverse(
                'posts:profile', kwargs={'username': cls.post_author.username})
        }


    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def get_count_paginator_group_list(self):
        group_response = self.authorized_user.get(self.url['group_list'])
        return group_response.context['page_obj'].paginator.count


    def setUp(self):
        self.guest_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)

    def test_authorized_user_create_post(self):
        """Проверка создания записи авторизированным клиентом."""
        count_before_db = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
            'image': self.uploaded
        }
        self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), count_before_db + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data['group'])

    def test_authorized_user_edit_post(self):
        """Проверка редактирования записи авторизированным автором."""
        post_created = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group_new.id,
        }
        response = self.authorized_user.post(
            reverse("posts:post_edit", args=(post_created.id,)),
            data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post_created.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post_edited = Post.objects.get(pk=post_created.id)
        self.assertEqual(post_edited.text, form_data['text'])
        self.assertEqual(post_edited.author, post_created.author)
        self.assertEqual(post_edited.pub_date, post_created.pub_date)
        self.assertEqual(post_edited.group_id, form_data['group'])

    def test_nonauthorized_user_create_post(self):
        """Проверка создания записи не авторизированным пользователем."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.guest_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_form_post_edit_authorised_client_nonauthor(self):
        '''Проверяем, что при авторизованном не авторе
        форма не редактирует запись'''
        post_for_edit = Post.objects.create(
            author=PostFormTests.post_author,
            text='Тестовый пост 2',
            group=self.group,
        )
        id_post = post_for_edit.id
        form_data = {
            'text': 'New',
            'group': self.group_new.id,
        }
        self.user2 = User.objects.create_user(username='Non_post_writer')
        self.authorised_client2 = Client()
        self.authorised_client2.force_login(self.user2)
        response = self.authorised_client2.post(
            reverse('posts:post_edit', kwargs={'post_id': id_post}),
            data=form_data,
        )
        post_edited = Post.objects.get(pk=id_post)
        self.assertEqual(post_edited.text, post_for_edit.text)
        self.assertEqual(post_edited.author, post_for_edit.author)
        self.assertEqual(post_edited.pub_date, post_for_edit.pub_date)
        self.assertEqual(post_edited.group, post_for_edit.group)
        self.assertRedirects(
            response, f'/posts/{id_post}/'
        )

    def test_edit_post_anonim(self):
        """Проверка при запросе неавторизованного пользователя
        пост не будет отредактирован."""
        post_for_edit = Post.objects.create(
            author=PostFormTests.post_author,
            text='Тестовый пост 2',
            group=self.group,
        )
        id_post = post_for_edit.id
        form_data = {
            'text': 'New',
            'group': self.group_new.id,
        }
        response = self.guest_user.post(
            reverse('posts:post_edit', kwargs={'post_id': id_post}),
            data=form_data,
        )
        post_edited = Post.objects.get(pk=id_post)
        self.assertEqual(post_edited.text, post_for_edit.text)
        self.assertEqual(post_edited.author, post_for_edit.author)
        self.assertEqual(post_edited.pub_date, post_for_edit.pub_date)
        self.assertEqual(post_edited.group, post_for_edit.group)
        self.assertRedirects(
            response, reverse("login") + "?next=" + reverse(
                "posts:post_edit", kwargs={"post_id": id_post})
        )

    def test_authorized_user_create_post_without_group(self):
        """Проверка создания записи авторизированным
        пользователем без группы."""
        count_before_db = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )

        self.assertEqual(Post.objects.count(), count_before_db + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertIsNone(post.group, count_before_db)
        count_after_db = Post.objects.count()
        self.assertEqual(count_after_db, count_before_db + 1)

    def test_guest_create_comment(self):
        """Проверка создания комментария гостем"""
        prev_count = Comment.objects.count()
        response = self.guest_user.post(
            self.url['comment'],
            data=self.form_comment_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        redirect = self.url['login'] + '?next=' + self.url['comment']
        self.assertRedirects(response, redirect)
        self.assertEqual(Comment.objects.count(), prev_count)

    def test_authorized_create_comment(self):
        """Проверка создания комментария авторизованным"""
        if Comment.objects.count() != 0:
            Comment.objects.all().delete()
        self.assertEqual(Comment.objects.count(), 0, 'база не очищена')
        prev_count = Comment.objects.count()
        response = self.authorized_user.post(
            self.url['comment'],
            data=self.form_comment_data,
            follow=True
        )
        self.assertRedirects(
            response,
            self.url['post_detail']
        )
        self.assertEqual(prev_count + 1, Comment.objects.count())
        self.assertTrue(
            Comment.objects.filter(text=self.form_comment_data['text'])
            .exists()
        )
        self.assertEqual(
            response.context['post'].comments.all()[0].text,
            self.form_comment_data['text']
        )
