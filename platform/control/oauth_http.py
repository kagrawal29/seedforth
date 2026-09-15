"""OAuth protocol routes. Human login/consent are separate required routes."""
import re

from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator, AuthenticationError
from mcp.server.auth.routes import create_auth_routes, cors_middleware, build_metadata
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import RequestBodyLimitMiddleware
from pydantic import AnyHttpUrl
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


def error(code, status=400):
    return JSONResponse({'error':code}, status_code=status,
                        headers={'Cache-Control':'no-store','Pragma':'no-cache'})


def auth_routes(provider):
    supported = ['mycelium'] + ['project:' + p for p in sorted(provider.allowed_projects)]
    registration = ClientRegistrationOptions(enabled=True, valid_scopes=supported, default_scopes=['mycelium'])
    revocation = RevocationOptions(enabled=True)
    routes = create_auth_routes(provider, AnyHttpUrl(provider.issuer),
        client_registration_options=registration, revocation_options=revocation)
    metadata = build_metadata(AnyHttpUrl(provider.issuer), None, registration, revocation)
    metadata.token_endpoint_auth_methods_supported = ['none']
    metadata.revocation_endpoint_auth_methods_supported = ['none']
    token_handler = TokenHandler(provider, ClientAuthenticator(provider))
    authorize_handler = AuthorizationHandler(provider)

    async def token(request):
        form = await request.form()
        if len(form.multi_items()) != len(form):
            return error('invalid_request')
        if form.get('resource') != provider.resource:
            return error('invalid_target')
        if form.get('grant_type') == 'authorization_code':
            verifier = form.get('code_verifier', '')
            if not isinstance(verifier, str) or not re.fullmatch('[A-Za-z0-9._~-]{43,128}', verifier):
                return error('invalid_request')
        try:
            return await token_handler.handle(request)
        except Exception:
            return error('temporarily_unavailable', 503)

    async def authorize(request):
        form = request.query_params if request.method == 'GET' else await request.form()
        if (len(form.multi_items()) != len(form)
                or form.get('code_challenge_method') != 'S256'):
            return error('invalid_request')
        return await authorize_handler.handle(request)

    async def revoke(request):
        form = await request.form()
        raw = form.get('token')
        if len(form.multi_items()) != len(form) or not isinstance(raw, str) or not 1 <= len(raw) <= 1024:
            return error('invalid_request')
        try:
            client = await ClientAuthenticator(provider).authenticate_request(request)
            await provider.revoke_presented(client, raw)
        except AuthenticationError:
            return error('invalid_client', 401)
        except Exception:
            return error('temporarily_unavailable', 503)
        return Response(status_code=200, headers={'Cache-Control':'no-store', 'Pragma':'no-cache'})

    result = []
    for route in routes:
        if route.path == '/token':
            route = Route('/token', endpoint=cors_middleware(token, ['POST', 'OPTIONS']), methods=['POST', 'OPTIONS'])
        elif route.path == '/authorize':
            route = Route('/authorize', endpoint=authorize, methods=['GET', 'POST'])
        elif route.path == '/revoke':
            route = Route('/revoke', endpoint=cors_middleware(revoke, ['POST', 'OPTIONS']), methods=['POST', 'OPTIONS'])
        elif route.path == '/.well-known/oauth-authorization-server':
            route = Route(route.path, endpoint=cors_middleware(MetadataHandler(metadata).handle, ['GET', 'OPTIONS']), methods=['GET', 'OPTIONS'])
        route.app = RequestBodyLimitMiddleware(route.app, 32768)
        result.append(route)
    return result
