package com.llmmax.webui.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientResponseException;

/**
 * Two distinct failure modes get two distinct responses:
 *   - agentd unreachable at all -> 502, generic "backend unavailable" message.
 *   - agentd reachable but returned an error (e.g. 503 Ollama not running,
 *     404 no tuned config yet) -> pass agentd's own status code and
 *     message straight through, since agentd already produced a correct,
 *     specific error for the situation.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(AgentdUnavailableException.class)
    public ResponseEntity<ErrorResponse> handleAgentdUnavailable(AgentdUnavailableException e) {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(new ErrorResponse(e.getMessage()));
    }

    @ExceptionHandler(RestClientResponseException.class)
    public ResponseEntity<ErrorResponse> handleAgentdErrorResponse(RestClientResponseException e) {
        return ResponseEntity.status(e.getStatusCode())
                .body(new ErrorResponse(extractDetail(e)));
    }

        private final com.fasterxml.jackson.databind.ObjectMapper objectMapper =
            new com.fasterxml.jackson.databind.ObjectMapper();

    private String extractDetail(RestClientResponseException e) {
        // agentd (FastAPI/HTTPException) returns {"detail": "..."} on errors.
        // Parsed directly from the raw body string (not via
        // e.getResponseBodyAs()) since that method requires message
        // converters wired into the exception at creation time — reliable
        // for exceptions RestClient builds internally, but not guaranteed
        // for exceptions constructed any other way. Parsing the raw string
        // ourselves works unconditionally.
        String body = e.getResponseBodyAsString();
        try {
            com.fasterxml.jackson.databind.JsonNode node = objectMapper.readTree(body);
            if (node.has("detail")) {
                return node.get("detail").asText();
            }
        } catch (Exception ignored) {
            // body wasn't JSON, or had no "detail" field — fall through
        }
        return body;
    }
}
