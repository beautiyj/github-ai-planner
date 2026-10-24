from django.urls import path
from . import views

urlpatterns = [
    path("repos/", views.RepoListView.as_view(), name="repo_list"),
    path("repos/detail/", views.RepoDetailView.as_view(), name="repo_detail"),
    path("commits/", views.CommitListView.as_view(), name="commit_list"),
]