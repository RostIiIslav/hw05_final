from django.db import models

from django.contrib.auth import get_user_model

from .const import COUNT


User = get_user_model()

IMAGE_DIRECTORY = 'posts/'


class Group(models.Model):
    title = models.CharField(max_length=200,
                             verbose_name='Заголовок',
                             help_text='Название группы')
    slug = models.SlugField(unique=True,
                            db_index=True,
                            verbose_name='slug')
    description = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Текст нового поста',
                            help_text='Введите текст поста')
    pub_date = models.DateTimeField(auto_now_add=True,
                                    verbose_name='Дата публикации')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор',
        help_text='Выберите автора'
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name='Группа',
        help_text='Выберите группу'
    )
    image = models.ImageField(
        'Картинка',
        upload_to=IMAGE_DIRECTORY,
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self) -> str:
        return self.text[:COUNT]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        related_name="comments",
        verbose_name="Пост",
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор",
        related_name="comments",
    )
    text = models.TextField(
        verbose_name="Текст комментария",
        blank=True)
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата комментария",
    )

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return self.text[:COUNT]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        related_name='follower',
        verbose_name="Подписчик",
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User,
        related_name='following',
        verbose_name="Тот на кого подписываются",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "author"),
                name="unique follow")
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.author.username}"
