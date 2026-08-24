package com.llmmax.webui.service;

import com.llmmax.webui.dto.*;
import com.llmmax.webui.exception.AgentdUnavailableException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class AgentdClientTest {

    private static final String BASE_URL = "http://localhost:8000";

    private MockRestServiceServer server;
    private AgentdClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        client = new AgentdClient(builder, BASE_URL);
    }

    @Test
    void scanHardware_mapsSnakeCaseJsonToCamelCaseDto() {
        server.expect(requestTo(BASE_URL + "/hardware/scan"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("""
                        {
                          "gpus": [
                            {"index": 0, "name": "Test GPU", "total_vram_mb": 8192,
                             "free_vram_mb": 6000, "used_vram_mb": 2192,
                             "compute_capability": "7.5", "utilization_pct": 10,
                             "temperature_c": 45}
                          ],
                          "cpu_cores_physical": 8,
                          "cpu_cores_logical": 16,
                          "cpu_model": "Test CPU",
                          "total_ram_mb": 16384,
                          "available_ram_mb": 8000
                        }
                        """, MediaType.APPLICATION_JSON));

        HardwareProfileDto result = client.scanHardware();

        assertThat(result.cpuCoresPhysical()).isEqualTo(8);
        assertThat(result.cpuCoresLogical()).isEqualTo(16);
        assertThat(result.totalRamMb()).isEqualTo(16384);
        assertThat(result.hasGpu()).isTrue();
        assertThat(result.gpus()).hasSize(1);
        assertThat(result.gpus().get(0).freeVramMb()).isEqualTo(6000);
        assertThat(result.gpus().get(0).computeCapability()).isEqualTo("7.5");

        server.verify();
    }

    @Test
    void listModels_mapsNestedModelSpecCorrectly() {
        server.expect(requestTo(BASE_URL + "/models"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("""
                        [
                          {
                            "model": {
                              "id": "llama3.2:1b", "display_name": "Llama 3.2 1B",
                              "family": "llama3.2", "param_size_b": 1.0,
                              "quantizations": ["Q4_K_M"], "min_vram_mb": 1500,
                              "recommended_vram_mb": 2500, "min_ram_mb": 4000,
                              "notes": null
                            },
                            "tier": "great_fit",
                            "reason": "comfortably fits"
                          }
                        ]
                        """, MediaType.APPLICATION_JSON));

        List<ModelCompatibilityDto> result = client.listModels();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).tier()).isEqualTo("great_fit");
        assertThat(result.get(0).model().id()).isEqualTo("llama3.2:1b");
        assertThat(result.get(0).model().displayName()).isEqualTo("Llama 3.2 1B");
        assertThat(result.get(0).model().recommendedVramMb()).isEqualTo(2500);

        server.verify();
    }

    @Test
    void run_mapsNestedRunRecordAndIgnoresUnmappedRawField() {
        server.expect(requestTo(BASE_URL + "/models/llama3-1b/run"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.prompt").value("hello"))
                .andRespond(withSuccess("""
                        {
                          "response": "Hi there!",
                          "total_duration_s": 1.5,
                          "tokens_generated": 20,
                          "tokens_per_sec": 13.3,
                          "raw": {"some": "ollama-internal-field-we-dont-model"},
                          "run_record": {
                            "id": 1, "model_id": "llama3.2:1b", "runtime": "ollama",
                            "prompt": "hello", "tokens_generated": 20,
                            "total_duration_s": 1.5, "tokens_per_sec": 13.3,
                            "created_at": "2026-01-01 00:00:00"
                          }
                        }
                        """, MediaType.APPLICATION_JSON));

        RunResultDto result = client.run("llama3-1b", "hello");

        assertThat(result.response()).isEqualTo("Hi there!");
        assertThat(result.runRecord().modelId()).isEqualTo("llama3.2:1b");
        assertThat(result.runRecord().id()).isEqualTo(1L);

        server.verify();
    }

    @Test
    void tune_mapsFullTuningSessionShape() {
        server.expect(requestTo(BASE_URL + "/models/llama3-1b/tune"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.dry_run").value(true))
                .andRespond(withSuccess("""
                        {
                          "model_id": "llama3.2:1b",
                          "baseline": {
                            "config": {"num_ctx": 2048},
                            "benchmark": {
                              "config": {"num_ctx": 2048}, "tokens_per_sec": 50.0,
                              "p50_latency_s": 1.0, "p95_latency_s": 1.2,
                              "oom_occurred": false, "error": null,
                              "samples_completed": 3, "samples_attempted": 3
                            }
                          },
                          "candidates": [],
                          "winner": {
                            "config": {"num_ctx": 2048},
                            "benchmark": {
                              "config": {"num_ctx": 2048}, "tokens_per_sec": 50.0,
                              "p50_latency_s": 1.0, "p95_latency_s": 1.2,
                              "oom_occurred": false, "error": null,
                              "samples_completed": 3, "samples_attempted": 3
                            }
                          },
                          "outcome": "kept_baseline",
                          "reason": "no improvement"
                        }
                        """, MediaType.APPLICATION_JSON));

        TuningSessionDto result = client.tune("llama3-1b", true);

        assertThat(result.outcome()).isEqualTo("kept_baseline");
        assertThat(result.winner().benchmark().tokensPerSec()).isEqualTo(50.0);
        assertThat(result.winner().benchmark().succeeded()).isTrue();
        assertThat(result.winner().config()).containsEntry("num_ctx", 2048);

        server.verify();
    }

    @Test
    void autopilotStatus_noConfigYet() {
        server.expect(requestTo(BASE_URL + "/autopilot/llama3-1b/status"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("""
                        {"model_id": "llama3.2:1b", "config": null, "is_locked": false,
                         "created_at": null, "has_config": false}
                        """, MediaType.APPLICATION_JSON));

        TunedConfigStatusDto result = client.autopilotStatus("llama3-1b");

        assertThat(result.hasConfig()).isFalse();
        assertThat(result.config()).isNull();

        server.verify();
    }

    @Test
    void agentdUnreachable_throwsAgentdUnavailableException() {
        // No server.expect() set up — MockRestServiceServer rejects any
        // request as "unexpected", simulating agentd simply not being there.
        server.expect(requestTo(BASE_URL + "/hardware/scan"))
                .andRespond(request -> {
                    throw new java.io.IOException("Connection refused");
                });

        assertThatThrownBy(() -> client.scanHardware())
                .isInstanceOf(AgentdUnavailableException.class)
                .hasMessageContaining("Could not reach agentd");
    }

    @Test
    void agentdErrorResponse_propagatesAsRestClientResponseException() {
        server.expect(requestTo(BASE_URL + "/models/llama3-1b/run"))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .body("{\"detail\": \"ollama runtime is not available\"}"));

        assertThatThrownBy(() -> client.run("llama3-1b", "hi"))
                .isInstanceOf(org.springframework.web.client.RestClientResponseException.class);
    }
}
