package com.llmmax.webui.controller;

import com.llmmax.webui.dto.GpuInfoDto;
import com.llmmax.webui.dto.HardwareProfileDto;
import com.llmmax.webui.dto.ModelCompatibilityDto;
import com.llmmax.webui.dto.ModelSpecDto;
import com.llmmax.webui.service.AgentdClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(HardwareController.class)
class HardwareControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AgentdClient agentdClient;

    @Test
    void scan_returnsHardwareProfileAsJson() throws Exception {
        var profile = new HardwareProfileDto(
                List.of(new GpuInfoDto(0, "Test GPU", 8192, 6000, 2192, "7.5", 10, 45)),
                8, 16, "Test CPU", 16384, 8000
        );
        when(agentdClient.scanHardware()).thenReturn(profile);

        mockMvc.perform(get("/api/hardware/scan"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.cpuCoresPhysical").value(8))
                .andExpect(jsonPath("$.gpus[0].name").value("Test GPU"))
                .andExpect(jsonPath("$.gpus[0].freeVramMb").value(6000));
    }

    @Test
    void models_returnsCompatibilityList() throws Exception {
        var spec = new ModelSpecDto("m:1b", "M 1B", "m", 1.0, List.of("Q4_K_M"), 1500, 2500, 4000, null);
        var compat = new ModelCompatibilityDto(spec, "great_fit", "fits comfortably");
        when(agentdClient.listModels()).thenReturn(List.of(compat));

        mockMvc.perform(get("/api/models"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].tier").value("great_fit"))
                .andExpect(jsonPath("$[0].model.id").value("m:1b"));
    }
}