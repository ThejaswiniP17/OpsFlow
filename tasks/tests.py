from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from teams.models import Team, TeamMember
from tasks.models import Task, Comment

User = get_user_model()

class OpsFlowTests(TestCase):
    def setUp(self):
        # Create Users
        self.admin = User.objects.create_user(
            username='admin_user', password='password123', email='admin@opsflow.com', role=User.ADMIN,
            first_name='Admin', last_name='User'
        )
        self.lead = User.objects.create_user(
            username='lead_user', password='password123', email='lead@opsflow.com', role=User.TEAM_LEAD,
            first_name='Lead', last_name='User'
        )
        self.member = User.objects.create_user(
            username='member_user', password='password123', email='member@opsflow.com', role=User.MEMBER,
            first_name='Member', last_name='User'
        )
        self.outsider = User.objects.create_user(
            username='outsider_user', password='password123', email='outsider@opsflow.com', role=User.MEMBER,
            first_name='Outsider', last_name='User'
        )

        # Create Team
        self.team = Team.objects.create(name="DevOps Team", description="Infrastructure & CI/CD", created_by=self.lead)
        
        # Add Members
        TeamMember.objects.create(team=self.team, user=self.lead, role=TeamMember.LEAD)
        TeamMember.objects.create(team=self.team, user=self.member, role=TeamMember.MEMBER)

        # Create Task
        self.task = Task.objects.create(
            title="Deploy Kubernetes Cluster",
            description="Set up EKS cluster for staging env",
            status=Task.PENDING,
            priority=Task.CRITICAL,
            team=self.team,
            created_by=self.lead,
            assigned_to=self.member
        )

    def test_user_roles(self):
        self.assertTrue(self.admin.is_admin())
        self.assertTrue(self.lead.is_team_lead())
        self.assertFalse(self.member.is_team_lead())
        self.assertTrue(self.member.is_member())

    def test_team_scoping_boundary(self):
        # Log in as the outsider (who does NOT belong to self.team)
        self.client.login(username='outsider_user', password='password123')
        
        # Try to view team details page
        response = self.client.get(reverse('teams:team_detail', kwargs={'pk': self.team.pk}))
        # Should return Permission Denied (403)
        self.assertEqual(response.status_code, 403)

        # Try to view task detail
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 403)

    def test_task_status_transition_by_member(self):
        # Log in as member (assigned to the task)
        self.client.login(username='member_user', password='password123')
        
        # Post quick status update: PENDING -> IN_PROGRESS
        response = self.client.post(
            reverse('tasks:quick_update', kwargs={'pk': self.task.pk}),
            {'action': 'status', 'status': Task.IN_PROGRESS}
        )
        
        self.assertEqual(response.status_code, 302) # Redirects back to detail page
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.IN_PROGRESS)

    def test_task_creation_permission(self):
        # Member cannot create tasks
        self.client.login(username='member_user', password='password123')
        response = self.client.post(
            reverse('tasks:task_create'),
            {'title': 'Hack Task', 'description': 'desc', 'team': self.team.pk, 'status': Task.PENDING, 'priority': Task.LOW}
        )
        self.assertEqual(response.status_code, 403)

        # Team Lead can create tasks
        self.client.login(username='lead_user', password='password123')
        response = self.client.post(
            reverse('tasks:task_create'),
            {
                'title': 'Setup Sentry Alerting', 
                'description': 'Configure alerting policies for errors', 
                'team': self.team.pk, 
                'status': Task.PENDING, 
                'priority': Task.HIGH
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title='Setup Sentry Alerting').exists())
