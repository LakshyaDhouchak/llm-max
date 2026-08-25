package com.llmmax.webui.exception;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Objects;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @ExceptionHandler(AgentdUnavailableException.class)
    public ResponseEntity<ErrorResponse> handleAgentdUnavailable(AgentdUnavailableException e) {
        return buildResponse(HttpStatus.BAD_GATEWAY, "AGENTD_UNAVAILABLE", e.getMessage());
    }

    @ExceptionHandler(RestClientResponseException.class)
    public ResponseEntity<ErrorResponse> handleAgentdErrorResponse(RestClientResponseException e) {
        return buildResponse(
                HttpStatus.valueOf(e.getStatusCode().value()),
                "AGENTD_ERROR",
                extractDetail(e)
        );
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        String message = Objects.requireNonNullElse(e.getBindingResult().getFieldError(), e.getBindingResult().getGlobalError())
                == null ? "Validation failed" : Objects.requireNonNullElse(e.getBindingResult().getFieldError(), e.getBindingResult().getGlobalError()).getDefaultMessage();
        return buildResponse(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", message);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleUnreadableBody(HttpMessageNotReadableException e) {
        return buildResponse(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", "Request payload is malformed or missing required fields.");
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ErrorResponse> handleConstraintViolation(ConstraintViolationException e) {
        return buildResponse(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneral(Exception e) {
        return buildResponse(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "An unexpected server error occurred.");
    }

    private ResponseEntity<ErrorResponse> buildResponse(HttpStatus status, String code, String message) {
        return ResponseEntity.status(status)
                .body(new ErrorResponse(status.value(), code, message, requestId()));
    }

    private String requestId() {
        var attrs = RequestContextHolder.getRequestAttributes();
        if (attrs instanceof ServletRequestAttributes servletRequestAttributes) {
            HttpServletRequest request = servletRequestAttributes.getRequest();
            Object requestId = request.getAttribute("requestId");
            if (requestId instanceof String value && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String extractDetail(RestClientResponseException e) {
        String body = e.getResponseBodyAsString();
        try {
            JsonNode node = OBJECT_MAPPER.readTree(body);
            if (node.has("detail")) {
                return node.get("detail").asText();
            }
            if (node.has("message")) {
                return node.get("message").asText();
            }
        } catch (Exception ignored) {
            // body wasn't JSON, or had no recognized error field — fall through
        }
        return body == null || body.isBlank() ? "Agentd request failed." : body;
    }
}
