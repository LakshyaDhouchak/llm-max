package com.llmmax.webui.controller;

import com.llmmax.webui.dto.HardwareProfileDto;
import com.llmmax.webui.dto.RunRecordDto;
import com.llmmax.webui.service.AgentdClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Collections;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(StatusController.class)
class StatusControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AgentdClient agentdClient;

    @Test
    void status_returnsHardwareProfile() throws Exception {
        var profile = new HardwareProfileDto(Collections.emptyList(), 4, 8, "CPU", 16000, 8000);
        when(agentdClient.status()).thenReturn(profile);

        mockMvc.perform(get("/api/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.cpuCoresPhysical").value(4));
    }

    @Test
    void history_defaultsToLimit20AndNullModelId() throws Exception {
        when(agentdClient.history(isNull(), eq(20))).thenReturn(List.of());

        mockMvc.perform(get("/api/history"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray());

        verify(agentdClient).history(isNull(), eq(20));
    }

    @Test
    void history_passesModelIdAndLimitThrough() throws Exception {
        var record = new RunRecordDto(1L, "m:1b", "ollama", "hi", 10, 1.0, 10.0, "2026-01-01");
        when(agentdClient.history(eq("m:1b"), eq(5))).thenReturn(List.of(record));

        mockMvc.perform(get("/api/history").param("modelId", "m:1b").param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].modelId").value("m:1b"))
                .andExpect(jsonPath("$[0].tokensPerSec").value(10.0));

        verify(agentdClient).history(eq("m:1b"), eq(5));
    }
}
