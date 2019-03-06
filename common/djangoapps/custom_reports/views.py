"""
Reports view functions
"""
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


# sample callback
@csrf_exempt
@require_POST
def my_callback(request):
    print(request.body)
    return JsonResponse({
        "success": True
    })


def download_csv_or_json(request, csv_or_json_file_name):
    if not request.user.is_superuser:
        return HttpResponse("You are not authenticated")
    try:
        with open('reports/{}'.format(csv_or_json_file_name), 'rb') as csv_or_json_file:
            response = HttpResponse(csv_or_json_file, content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(csv_or_json_file_name)
            return response
    except IOError:
        return HttpResponse('No such file found')
