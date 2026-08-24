package com.llmmax.webui.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Liveness check, matching agentd's own GET /health — lets you (or a
 * future docker-compose healthcheck) confirm this service is up
 * independent of whether agentd or Ollama are reachable.
 */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
