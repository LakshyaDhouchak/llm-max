package com.llmmax.webui.exception;

/**
 * Thrown when agentd itself cannot be reached at all — connection refused,
 * DNS failure, timeout. Distinct from agentd returning a real HTTP error
 * response (e.g. 503 because Ollama isn't running, which agentd itself
 * already reports correctly and we simply pass through).
 */
public class AgentdUnavailableException extends RuntimeException {
    public AgentdUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}