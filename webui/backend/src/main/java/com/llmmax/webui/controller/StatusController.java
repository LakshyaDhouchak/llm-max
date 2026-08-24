package com.llmmax.webui.controller;

import com.llmmax.webui.dto.HardwareProfileDto;
import com.llmmax.webui.dto.RunRecordDto;
import com.llmmax.webui.service.AgentdClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api")
public class StatusController {

    private final AgentdClient agentdClient;

    public StatusController(AgentdClient agentdClient) {
        this.agentdClient = agentdClient;
    }

    @GetMapping("/status")
    public HardwareProfileDto status() {
        return agentdClient.status();
    }

    @GetMapping("/history")
    public List<RunRecordDto> history(
            @RequestParam(required = false) String modelId,
            @RequestParam(defaultValue = "20") int limit
    ) {
        return agentdClient.history(modelId, limit);
    }
}