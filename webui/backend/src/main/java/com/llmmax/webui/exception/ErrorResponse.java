package com.llmmax.webui.exception;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {
    private final Instant timestamp;
    private final int status;
    private final String code;
    private final String message;
    private final String requestId;

    public ErrorResponse(String message) {
        this(500, "INTERNAL_ERROR", message, null);
    }

    public ErrorResponse(int status, String code, String message, String requestId) {
        this.timestamp = Instant.now();
        this.status = status;
        this.code = code;
        this.message = message;
        this.requestId = requestId;
    }

    public Instant timestamp() {
        return timestamp;
    }

    public int status() {
        return status;
    }

    public String code() {
        return code;
    }

    public String message() {
        return message;
    }

    public String requestId() {
        return requestId;
    }

    @JsonProperty("error")
    public String getError() {
        return message;
    }
}