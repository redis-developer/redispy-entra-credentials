from typing import Self, Union, Tuple, Callable, Any

from redis.credentials import StreamingCredentialProvider
from redisauth.token_manager import TokenManagerConfig, RetryPolicy, TokenManager, CredentialsListener

from entraid.identity_provider import EntraIDIdentityProvider


class TokenAuthConfig:
    """
    Configuration for token authentication.

    Requires :class:`EntraIDIdentityProvider`. It's recommended to use an additional factory methods.
    See :class:`EntraIDIdentityProvider` for more information.
    """
    def __init__(self, idp: EntraIDIdentityProvider):
        self._expiration_refresh_ratio = 0.8
        self._lower_refresh_bound_millis = 0
        self._token_request_execution_timeout_in_ms = 100
        self._max_attempts = 3
        self._delay_in_ms = 10
        self._idp = idp

    def get_token_manager_config(self) -> TokenManagerConfig:
        return TokenManagerConfig(
            self._expiration_refresh_ratio,
            self._lower_refresh_bound_millis,
            self._token_request_execution_timeout_in_ms,
            RetryPolicy(
                self._max_attempts,
                self._delay_in_ms
            )
        )

    def get_identity_provider(self) -> EntraIDIdentityProvider:
        return self._idp

    def expiration_refresh_ratio(self, value: float) -> Self:
        """
        Percentage value of total token TTL when refresh should be triggered.
        Default: 0.8

        :param value: float
        :return: Self
        """
        self._expiration_refresh_ratio = value
        return self

    def lower_refresh_bound_millis(self, value: int) -> Self:
        """
        Represents the minimum time in milliseconds before token expiration to trigger a refresh, in milliseconds.
        Default: 0

        :param value: int
        :return: Self
        """
        self._lower_refresh_bound_millis = value
        return self

    def token_request_execution_timeout_in_ms(self, value: int) -> Self:
        """
        Represents the maximum time in milliseconds to wait for a token request to complete.
        Default: 100

        :param value: int
        :return: Self
        """
        self._token_request_execution_timeout_in_ms = value
        return self

    def max_attempts(self, value: int) -> Self:
        """
        Represents the maximum number of attempts to trigger a refresh in case of error.
        Default: 3

        :param value: int
        :return: Self
        """
        self._max_attempts = value
        return self

    def delay_in_ms(self, value: int) -> Self:
        """
        Represents the delay between retries.
        Default: 10

        :param value: int
        :return: Self
        """
        self._delay_in_ms = value
        return self


class EntraIdCredentialsProvider(StreamingCredentialProvider):
    def __init__(self, config: TokenAuthConfig):
        self._token_mgr = TokenManager(
            config.get_identity_provider(),
            config.get_token_manager_config()
        )
        self._listener = CredentialsListener()
        self._is_streaming = False

    def get_credentials(self) -> Union[Tuple[str], Tuple[str, str]]:
        init_token = self._token_mgr.acquire_token()

        if self._is_streaming is False:
            self._token_mgr.start(
                self._listener
            )
            self._is_streaming = True

        return init_token.get_token().try_get('oid'), init_token.get_token().get_value()

    def on_next(self, callback: Callable[[Any], None]):
        self._listener.on_next = callback

    def on_error(self, callback: Callable[[Exception], None]):
        self._listener.on_error = callback

    def is_streaming(self) -> bool:
        return self._is_streaming