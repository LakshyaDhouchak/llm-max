package com.llmmax.webui.controller;

import com.llmmax.webui.dto.HardwareProfileDto;
import com.llmmax.webui.dto.ModelCompatibilityDto;
import com.llmmax.webui.service.AgentdClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping({"/api", "/api/v1"})
public class HardwareController {

    private final AgentdClient agentdClient;

    public HardwareController(AgentdClient agentdClient) {
        this.agentdClient = agentdClient;
    }

    @GetMapping({"/hardware", "/hardware/scan"})
    public HardwareProfileDto scan() {
        return agentdClient.scanHardware();
    }

    @GetMapping({"/models", "/recommendations"})
    public List<ModelCompatibilityDto> models() {
        return agentdClient.listModels();
    }

    @GetMapping("/models/{modelId}")
    public ModelCompatibilityDto model(@org.springframework.web.bind.annotation.PathVariable String modelId) {
        return agentdClient.listModels().stream()
                .filter(item -> item.model() != null && item.model().id().equalsIgnoreCase(modelId))
                .findFirst()
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND,
                        "Model '%s' not found".formatted(modelId)
                ));
    }
}