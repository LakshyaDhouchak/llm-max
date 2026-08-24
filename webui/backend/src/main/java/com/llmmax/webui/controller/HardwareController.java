package com.llmmax.webui.controller;

import com.llmmax.webui.dto.HardwareProfileDto;
import com.llmmax.webui.dto.ModelCompatibilityDto;
import com.llmmax.webui.service.AgentdClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api")
public class HardwareController {

    private final AgentdClient agentdClient;

    public HardwareController(AgentdClient agentdClient) {
        this.agentdClient = agentdClient;
    }

    @GetMapping("/hardware/scan")
    public HardwareProfileDto scan() {
        return agentdClient.scanHardware();
    }

    @GetMapping("/models")
    public List<ModelCompatibilityDto> models() {
        return agentdClient.listModels();
    }
}