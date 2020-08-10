from unittest import TestCase
from unittest.mock import Mock

from samcli.local.events.api_event import ContextIdentity, RequestContext, ApiGatewayLambdaEvent


class TestContextIdentity(TestCase):
    def test_class_initialized(self):
        identity = ContextIdentity(
            "api_key",
            "user_arn",
            "cognito_authentication_type",
            "caller",
            "user_agent",
            "user",
            "cognito_identity_pool_id",
            "cognito_authentication_provider",
            "source_ip",
            "account_id",
        )

        self.assertEqual(identity.api_key, "api_key")
        self.assertEqual(identity.user_arn, "user_arn")
        self.assertEqual(identity.cognito_authentication_type, "cognito_authentication_type")
        self.assertEqual(identity.caller, "caller")
        self.assertEqual(identity.user_agent, "user_agent")
        self.assertEqual(identity.user, "user")
        self.assertEqual(identity.cognito_identity_pool_id, "cognito_identity_pool_id")
        self.assertEqual(identity.cognito_authentication_provider, "cognito_authentication_provider")
        self.assertEqual(identity.source_ip, "source_ip")
        self.assertEqual(identity.account_id, "account_id")

    def test_to_dict(self):
        identity = ContextIdentity(
            "api_key",
            "user_arn",
            "cognito_authentication_type",
            "caller",
            "user_agent",
            "user",
            "cognito_identity_pool_id",
            "cognito_authentication_provider",
            "source_ip",
            "account_id",
        )

        expected = {
            "apiKey": "api_key",
            "userArn": "user_arn",
            "cognitoAuthenticationType": "cognito_authentication_type",
            "caller": "caller",
            "userAgent": "user_agent",
            "user": "user",
            "cognitoIdentityPoolId": "cognito_identity_pool_id",
            "cognitoAuthenticationProvider": "cognito_authentication_provider",
            "sourceIp": "source_ip",
            "accountId": "account_id",
        }

        self.assertEqual(identity.to_dict(), expected)

    def test_to_dict_with_defaults(self):
        identity = ContextIdentity()

        expected = {
            "apiKey": None,
            "userArn": None,
            "cognitoAuthenticationType": None,
            "caller": None,
            "userAgent": "Custom User Agent String",
            "user": None,
            "cognitoIdentityPoolId": None,
            "cognitoAuthenticationProvider": None,
            "sourceIp": "127.0.0.1",
            "accountId": None,
        }

        self.assertEqual(identity.to_dict(), expected)


class TestRequestContext(TestCase):
    def test_class_initialized(self):
        identity_mock = Mock()

        request_context = RequestContext(
            "resource_id",
            "api_id",
            "request_path",
            "request_method",
            "request_id",
            "account_id",
            "prod",
            identity_mock,
            "extended_request_id",
            "path",
            "protocol",
            "domain_name",
            "request_time_epoch",
            "request_time",
        )

        self.assertEqual(request_context.resource_id, "resource_id")
        self.assertEqual(request_context.api_id, "api_id")
        self.assertEqual(request_context.resource_path, "request_path")
        self.assertEqual(request_context.http_method, "request_method")
        self.assertEqual(request_context.request_id, "request_id")
        self.assertEqual(request_context.account_id, "account_id")
        self.assertEqual(request_context.stage, "prod")
        self.assertEqual(request_context.identity, identity_mock)
        self.assertEqual(request_context.extended_request_id, "extended_request_id")
        self.assertEqual(request_context.path, "path")
        self.assertEqual(request_context.protocol, "protocol")
        self.assertEqual(request_context.domain_name, "domain_name")
        self.assertEqual(request_context.request_time_epoch, "request_time_epoch")
        self.assertEqual(request_context.request_time, "request_time")

    def test_to_dict(self):
        identity_mock = Mock()
        identity_mock.to_dict.return_value = {"identity": "the identity"}

        request_context = RequestContext(
            "resource_id",
            "api_id",
            "request_path",
            "request_method",
            "request_id",
            "account_id",
            "prod",
            identity_mock,
            "extended_request_id",
            "path",
            "protocol",
            "domain_name",
            "request_time_epoch",
            "request_time",
        )

        expected = {
            "resourceId": "resource_id",
            "apiId": "api_id",
            "resourcePath": "request_path",
            "httpMethod": "request_method",
            "requestId": "request_id",
            "accountId": "account_id",
            "stage": "prod",
            "identity": {"identity": "the identity"},
            "extendedRequestId": "extended_request_id",
            "path": "path",
            "protocol": "protocol",
            "domainName": "domain_name",
            "requestTimeEpoch": "request_time_epoch",
            "requestTime": "request_time",
        }

        self.assertEqual(request_context.to_dict(), expected)

    def test_to_dict_with_defaults(self):
        request_context = RequestContext(request_time="request_time", request_time_epoch="request_time_epoch")

        expected = {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": None,
            "httpMethod": None,
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "stage": None,
            "identity": {},
            "extendedRequestId": None,
            "path": None,
            "protocol": None,
            "domainName": None,
            "requestTimeEpoch": "request_time_epoch",
            "requestTime": "request_time",
        }

        self.assertEqual(request_context.to_dict(), expected)


class TestApiGatewayLambdaEvent(TestCase):
    def test_class_initialized(self):
        event = ApiGatewayLambdaEvent(
            "request_method",
            "request_data",
            "resource",
            "request_context",
            {"query": "some query"},
            {"query": ["some query"]},
            {"header_key": "value"},
            {"header_key": ["value"]},
            {"param": "some param"},
            {"stage_vars": "some vars"},
            "request_path",
            False,
        )

        self.assertEqual(event.http_method, "request_method")
        self.assertEqual(event.body, "request_data")
        self.assertEqual(event.resource, "resource")
        self.assertEqual(event.request_context, "request_context")
        self.assertEqual(event.query_string_params, {"query": "some query"})
        self.assertEqual(event.headers, {"header_key": "value"})
        self.assertEqual(event.path_parameters, {"param": "some param"})
        self.assertEqual(event.stage_variables, {"stage_vars": "some vars"})
        self.assertEqual(event.path, "request_path")
        self.assertEqual(event.is_base_64_encoded, False)

    def test_to_dict(self):
        request_context_mock = Mock()
        request_context_mock.to_dict.return_value = {"request_context": "the request context"}

        event = ApiGatewayLambdaEvent(
            "request_method",
            "request_data",
            "resource",
            request_context_mock,
            {"query": "some query"},
            {"query": ["first query", "some query"]},
            {"header_key": "value"},
            {"header_key": ["value"]},
            {"param": "some param"},
            {"stagevars": "some vars"},
            "request_path",
            False,
        )

        expected = {
            "httpMethod": "request_method",
            "body": "request_data",
            "resource": "resource",
            "requestContext": {"request_context": "the request context"},
            "queryStringParameters": {"query": "some query"},
            "multiValueQueryStringParameters": {"query": ["first query", "some query"]},
            "headers": {"header_key": "value"},
            "multiValueHeaders": {"header_key": ["value"]},
            "pathParameters": {"param": "some param"},
            "stageVariables": {"stagevars": "some vars"},
            "path": "request_path",
            "isBase64Encoded": False,
        }

        self.assertEqual(event.to_dict(), expected)

    def test_to_dict_with_defaults(self):
        event = ApiGatewayLambdaEvent()

        expected = {
            "httpMethod": None,
            "body": None,
            "resource": None,
            "requestContext": {},
            "queryStringParameters": None,
            "multiValueQueryStringParameters": None,
            "headers": None,
            "multiValueHeaders": None,
            "pathParameters": None,
            "stageVariables": None,
            "path": None,
            "isBase64Encoded": False,
        }

        self.assertEqual(event.to_dict(), expected)

    def test_init_with_invalid_query_string_params(self):
        with self.assertRaises(TypeError):
            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                "not a dict",
                {"query": ["first query", "some query"]},
                {"header_key": "value"},
                {"header_key": ["value"]},
                {"param": "some param"},
                {"stage_vars": "some vars"},
                "request_path",
                False,
            )

    def test_init_with_invalid_multi_value_query_string_params(self):
        with self.assertRaises(TypeError):
            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                {"query": "some query"},
                "not a dict",
                {"header_key": "value"},
                {"header_key": ["value"]},
                {"param": "some param"},
                {"stage_vars": "some vars"},
                "request_path",
                False,
            )

    def test_init_with_invalid_headers(self):
        with self.assertRaises(TypeError):
            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                {"query": "some query"},
                {"query": ["first query", "some query"]},
                "not EnvironHeaders",
                {"header_key": ["value"]},
                {"param": "some param"},
                {"stage_vars": "some vars"},
                "request_path",
                False,
            )

    def test_init_with_invalid_multi_value_headers(self):
        with self.assertRaises(TypeError):
            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                {"query": "some query"},
                {"query": ["first query", "some query"]},
                {"header_key": "value"},
                "not EnvironHeaders",
                {"param": "some param"},
                {"stage_vars": "some vars"},
                "request_path",
                False,
            )

    def test_init_with_invalid_path_parameters(self):
        with self.assertRaises(TypeError):
            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                {"query": "some query"},
                {"query": ["first query", "some query"]},
                {"header_key": "value"},
                {"header_key": ["value"]},
                "Not a dict",
                {"stage_vars": "some vars"},
                "request_path",
                False,
            )

    def test_init_with_invalid_stage_variables(self):
        with self.assertRaises(TypeError):

            ApiGatewayLambdaEvent(
                "request_method",
                "request_data",
                "resource",
                "request_context",
                {"query": "some query"},
                {"query": ["first query", "some query"]},
                {"header_key": "value"},
                {"header_key": ["value"]},
                {"param": "some param"},
                "Not a dict",
                "request_path",
                False,
            )
