package com.llmmax.webui.controller;

import com.llmmax.webui.dto.TunedConfigStatusDto;
import com.llmmax.webui.service.AgentdClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.HttpClientErrorException;

import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(RecommendationController.class)
class RecommendationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AgentdClient agentdClient;

    @Test
    void status_withConfig() throws Exception {
        var status = new TunedConfigStatusDto("m:1b", Map.of("num_ctx", 2048), false, "2026-01-01", true);
        when(agentdClient.autopilotStatus("m:1b")).thenReturn(status);

        mockMvc.perform(get("/api/autopilot/m:1b/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hasConfig").value(true))
                .andExpect(jsonPath("$.config.num_ctx").value(2048));
    }

    @Test
    void status_noConfigYet() throws Exception {
        var status = new TunedConfigStatusDto("m:1b", null, false, null, false);
        when(agentdClient.autopilotStatus("m:1b")).thenReturn(status);

        mockMvc.perform(get("/api/autopilot/m:1b/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hasConfig").value(false));
    }

    @Test
    void disable_success() throws Exception {
        doNothing().when(agentdClient).autopilotDisable("m:1b");

        mockMvc.perform(post("/api/autopilot/m:1b/disable"))
                .andExpect(status().isOk());

        verify(agentdClient).autopilotDisable("m:1b");
    }

    @Test
    void disable_noConfigYet_propagates404WithDetail() throws Exception {
        HttpClientErrorException upstream = HttpClientErrorException.create(
                HttpStatus.NOT_FOUND, "Not Found", HttpHeaders.EMPTY,
                "{\"detail\":\"No tuned config exists yet for m:1b — run tune first.\"}"
                        .getBytes(StandardCharsets.UTF_8),
                StandardCharsets.UTF_8
        );
        doThrow(upstream).when(agentdClient).autopilotDisable("m:1b");

        mockMvc.perform(post("/api/autopilot/m:1b/disable"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("No tuned config exists yet for m:1b — run tune first."));
    }
}
