package com.llmmax.webui.controller;

import com.llmmax.webui.dto.TunedConfigStatusDto;
import com.llmmax.webui.service.AgentdClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Mirrors agentd's own scoping decision: autopilot "enable" is not
 * exposed here either. See agentd/app/routes/recommendations.py's
 * docstring for the reasoning — it applies unchanged at this layer.
 */
@RestController
@RequestMapping({"/api/autopilot", "/api/v1/autopilot"})
public class RecommendationController {

    private final AgentdClient agentdClient;

    public RecommendationController(AgentdClient agentdClient) {
        this.agentdClient = agentdClient;
    }

    @GetMapping("/{modelId}/status")
    public TunedConfigStatusDto status(@PathVariable String modelId) {
        return agentdClient.autopilotStatus(modelId);
    }

    @PostMapping("/{modelId}/disable")
    public ResponseEntity<Void> disable(@PathVariable String modelId) {
        agentdClient.autopilotDisable(modelId);
        return ResponseEntity.ok().build();
    }
}