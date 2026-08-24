package com.llmmax.webui.controller;

import com.llmmax.webui.dto.*;
import com.llmmax.webui.exception.AgentdUnavailableException;
import com.llmmax.webui.service.AgentdClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.HttpClientErrorException;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ModelController.class)
class ModelControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AgentdClient agentdClient;

    private RunRecordDto sampleRunRecord() {
        return new RunRecordDto(1L, "m:1b", "ollama", "hi", 10, 1.0, 10.0, "2026-01-01");
    }

    @Test
    void run_success() throws Exception {
        var result = new RunResultDto("Hello!", 1.0, 10, 10.0, sampleRunRecord());
        when(agentdClient.run(eq("m:1b"), eq("hi"))).thenReturn(result);

        mockMvc.perform(post("/api/models/m:1b/run")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"prompt\":\"hi\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.response").value("Hello!"))
                .andExpect(jsonPath("$.runRecord.modelId").value("m:1b"));
    }

    @Test
    void run_blankPrompt_returns400() throws Exception {
        mockMvc.perform(post("/api/models/m:1b/run")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"prompt\":\"\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void run_agentdUnreachable_returns502() throws Exception {
        when(agentdClient.run(anyString(), anyString()))
                .thenThrow(new AgentdUnavailableException("Could not reach agentd — is it running?", null));

        mockMvc.perform(post("/api/models/m:1b/run")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"prompt\":\"hi\"}"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error").value("Could not reach agentd — is it running?"));
    }

    @Test
    void run_agentdReturns503_passesThroughStatusAndDetail() throws Exception {
        HttpClientErrorException upstream = HttpClientErrorException.create(
                HttpStatus.SERVICE_UNAVAILABLE, "Service Unavailable", HttpHeaders.EMPTY,
                "{\"detail\":\"ollama runtime is not available\"}".getBytes(StandardCharsets.UTF_8),
                StandardCharsets.UTF_8
        );
        when(agentdClient.run(anyString(), anyString())).thenThrow(upstream);

        mockMvc.perform(post("/api/models/m:1b/run")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"prompt\":\"hi\"}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error").value("ollama runtime is not available"));
    }

    @Test
    void tune_withDryRunTrue() throws Exception {
        var baseline = new TuningCandidateResultDto(
                Map.of("num_ctx", 2048),
                new BenchmarkResultDto(Map.of("num_ctx", 2048), 50.0, 1.0, 1.2, false, null, 3, 3)
        );
        var session = new TuningSessionDto("m:1b", baseline, List.of(), baseline, "kept_baseline", "no improvement");
        when(agentdClient.tune(eq("m:1b"), eq(true))).thenReturn(session);

        mockMvc.perform(post("/api/models/m:1b/tune")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"dryRun\":true}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.outcome").value("kept_baseline"));
    }

    @Test
    void tune_withNoBody_defaultsDryRunToFalse() throws Exception {
        var baseline = new TuningCandidateResultDto(
                Map.of("num_ctx", 2048),
                new BenchmarkResultDto(Map.of("num_ctx", 2048), 50.0, 1.0, 1.2, false, null, 3, 3)
        );
        var session = new TuningSessionDto("m:1b", baseline, List.of(), baseline, "kept_baseline", "no improvement");
        when(agentdClient.tune(eq("m:1b"), eq(false))).thenReturn(session);

        mockMvc.perform(post("/api/models/m:1b/tune"))
                .andExpect(status().isOk());
    }
}
