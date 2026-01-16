"""
CPD Export Service - Generate CPD reports in multiple formats.
"""

import csv
import io
import json
from datetime import date
from decimal import Decimal

from django.http import HttpResponse

from certificates.models import Certificate


class CPDExportService:
    """Service to generate CPD reports."""

    def __init__(self, user):
        self.user = user

    def get_cpd_data(self, start_date: date | None = None, end_date: date | None = None, cpd_type: str | None = None):
        """
        Gather all CPD data for the user.

        Returns:
            dict: Structured CPD data for export
        """
        from accounts.models import CPDRequirement

        # Get requirements
        requirements = CPDRequirement.objects.filter(user=self.user, is_active=True)
        if cpd_type:
            requirements = requirements.filter(cpd_type=cpd_type)

        # Get certificates (credits earned)
        certificates = Certificate.objects.filter(
            registration__user=self.user,
            status='active',
        ).select_related('registration__event')

        if start_date:
            certificates = certificates.filter(created_at__date__gte=start_date)
        if end_date:
            certificates = certificates.filter(created_at__date__lte=end_date)

        # Build data structure
        requirements_data = []
        for req in requirements:
            start, end = req.get_current_period_bounds()
            requirements_data.append({
                'cpd_type': req.cpd_type,
                'cpd_type_display': req.cpd_type_display or req.cpd_type,
                'annual_requirement': float(req.annual_requirement),
                'earned_credits': float(req.get_earned_credits()),
                'completion_percent': req.completion_percent,
                'period_start': start.isoformat(),
                'period_end': end.isoformat(),
                'licensing_body': req.licensing_body,
                'license_number': req.license_number,
            })

        credits_data = []
        for cert in certificates:
            event = cert.registration.event if cert.registration else None
            credits_data.append({
                'date': cert.created_at.strftime('%Y-%m-%d'),
                'event_title': event.title if event else 'N/A',
                'cpd_type': cert.certificate_data.get('cpd_type', 'general'),
                'credits': float(cert.certificate_data.get('cpd_credits', 0)),
                'certificate_id': cert.short_code or str(cert.uuid)[:8],
                'accreditation': event.cpd_accreditation_note if event else '',
            })

        return {
            'user': {
                'name': self.user.full_name,
                'email': self.user.email,
                'professional_title': self.user.professional_title,
            },
            'generated_at': date.today().isoformat(),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'requirements': requirements_data,
            'credits': credits_data,
            'summary': {
                'total_credits': sum(c['credits'] for c in credits_data),
                'total_events': len(credits_data),
            },
        }

    def export_json(self, **filters) -> HttpResponse:
        """Export as JSON."""
        data = self.get_cpd_data(**filters)
        content = json.dumps(data, indent=2, default=str)
        response = HttpResponse(content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="cpd_report_{date.today()}.json"'
        return response

    def export_csv(self, **filters) -> HttpResponse:
        """Export as CSV."""
        data = self.get_cpd_data(**filters)
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['CPD Credit Report'])
        writer.writerow([f'Generated: {data["generated_at"]}'])
        writer.writerow([f'Name: {data["user"]["name"]}'])
        writer.writerow([])

        # Requirements summary
        writer.writerow(['Requirements Summary'])
        writer.writerow(['Type', 'Required', 'Earned', 'Completion %', 'Licensing Body', 'License #'])
        for req in data['requirements']:
            writer.writerow([
                req['cpd_type_display'],
                req['annual_requirement'],
                req['earned_credits'],
                f"{req['completion_percent']}%",
                req['licensing_body'],
                req['license_number'],
            ])
        writer.writerow([])

        # Credit details
        writer.writerow(['Credit Details'])
        writer.writerow(['Date', 'Event', 'Type', 'Credits', 'Certificate ID'])
        for credit in data['credits']:
            writer.writerow([
                credit['date'],
                credit['event_title'],
                credit['cpd_type'],
                credit['credits'],
                credit['certificate_id'],
            ])
        writer.writerow([])
        writer.writerow([f'Total Credits: {data["summary"]["total_credits"]}'])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="cpd_report_{date.today()}.csv"'
        return response

    def export_txt(self, **filters) -> HttpResponse:
        """Export as plain text."""
        data = self.get_cpd_data(**filters)
        lines = [
            '=' * 60,
            'CPD CREDIT REPORT',
            '=' * 60,
            '',
            f'Name: {data["user"]["name"]}',
            f'Email: {data["user"]["email"]}',
            f'Generated: {data["generated_at"]}',
            '',
            '-' * 60,
            'REQUIREMENTS SUMMARY',
            '-' * 60,
        ]

        for req in data['requirements']:
            lines.extend([
                f'{req["cpd_type_display"]}:',
                f'  Required: {req["annual_requirement"]} credits',
                f'  Earned: {req["earned_credits"]} credits',
                f'  Progress: {req["completion_percent"]}%',
                f'  Period: {req["period_start"]} to {req["period_end"]}',
                f'  Licensing Body: {req["licensing_body"] or "N/A"}',
                f'  License #: {req["license_number"] or "N/A"}',
                '',
            ])

        lines.extend([
            '-' * 60,
            'CREDIT DETAILS',
            '-' * 60,
        ])

        for credit in data['credits']:
            lines.extend([
                f'{credit["date"]} | {credit["event_title"]}',
                f'  Type: {credit["cpd_type"]} | Credits: {credit["credits"]}',
                f'  Certificate: {credit["certificate_id"]}',
                '',
            ])

        lines.extend([
            '=' * 60,
            f'TOTAL CREDITS EARNED: {data["summary"]["total_credits"]}',
            '=' * 60,
        ])

        content = '\n'.join(lines)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="cpd_report_{date.today()}.txt"'
        return response

    def export_pdf(self, **filters) -> HttpResponse:
        """
        Export as PDF.

        Returns PDF bytes for client-side generation or minimal server-side PDF.
        For simplicity, returns JSON data that frontend can use with jsPDF.
        """
        # For elegant simplicity, return JSON that frontend renders to PDF
        # This avoids heavy server-side PDF dependencies
        data = self.get_cpd_data(**filters)
        content = json.dumps(data, indent=2, default=str)
        response = HttpResponse(content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="cpd_report_{date.today()}.json"'
        response['X-PDF-Hint'] = 'true'  # Signal to frontend to render as PDF
        return response
