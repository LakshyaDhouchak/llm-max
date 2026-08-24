package com.llmmax.webui.controller;

import com.llmmax.webui.dto.RunRequestDto;
import com.llmmax.webui.dto.RunResultDto;
import com.llmmax.webui.dto.TuneRequestDto;
import com.llmmax.webui.dto.TuningSessionDto;
import com.llmmax.webui.service.AgentdClient;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/models")
public class ModelController {

    private final AgentdClient agentdClient;

    public ModelController(AgentdClient agentdClient) {
        this.agentdClient = agentdClient;
    }

    @PostMapping("/{modelId}/run")
    public RunResultDto run(@PathVariable String modelId, @Valid @RequestBody RunRequestDto request) {
        return agentdClient.run(modelId, request.prompt());
    }

    @PostMapping("/{modelId}/tune")
    public TuningSessionDto tune(@PathVariable String modelId, @RequestBody(required = false) TuneRequestDto request) {
        boolean dryRun = request != null && request.dryRun();
        return agentdClient.tune(modelId, dryRun);
    }
}