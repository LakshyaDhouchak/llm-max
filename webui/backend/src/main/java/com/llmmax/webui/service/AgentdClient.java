package com.llmmax.webui.service;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.llmmax.webui.dto.*;
import com.llmmax.webui.exception.AgentdUnavailableException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * Wraps every HTTP call to agentd behind typed Java methods. Controllers
 * depend on this, never on RestClient directly — this is the one place
 * that knows agentd's URL shapes and error semantics, so a change to
 * agentd's API touches one file, not every controller.
 *
 * Uses its own dedicated ObjectMapper (snake_case naming strategy) rather
 * than Spring's globally-configured one, since agentd is a Python/pydantic
 * service and returns snake_case JSON (cpu_cores_physical, model_id, ...)
 * while our own webui API stays camelCase, the normal Java/JS convention,
 * for the frontend. Scoping the naming strategy to just this client keeps
 * those two concerns from leaking into each other.
 *
 * Note: /models/{id}/pull (streamed NDJSON progress) is deliberately not
 * wrapped here yet — proxying a streaming response through Spring is a
 * separate design decision (buffer vs. true stream-through to the
 * frontend) worth making deliberately once the frontend exists, not
 * bolted on here as a side effect.
 */
@Component
public class AgentdClient {

    private final RestClient restClient;

    @org.springframework.beans.factory.annotation.Autowired
    public AgentdClient(
            @Value("${llmmax.agentd.base-url}") String baseUrl,
            @Value("${llmmax.agentd.connect-timeout-ms}") int connectTimeoutMs,
            @Value("${llmmax.agentd.read-timeout-ms}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);

        this.restClient = configureAgentdJson(RestClient.builder())
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    /**
     * Test-only constructor: accepts a builder that may already be bound to
     * MockRestServiceServer, which installs its own mock ClientHttpRequestFactory
     * on the builder. Deliberately does NOT call .requestFactory(...) here —
     * doing so would silently replace/break the mock's factory (this is
     * exactly the bug this constructor split fixes: the original single
     * constructor always called .requestFactory(), which overwrote
     * MockRestServiceServer's factory and sent tests over the real network).
     */
    AgentdClient(RestClient.Builder builder, String baseUrl) {
        this.restClient = configureAgentdJson(builder).baseUrl(baseUrl).build();
    }

    private static RestClient.Builder configureAgentdJson(RestClient.Builder builder) {
        ObjectMapper agentdMapper = new ObjectMapper();
        agentdMapper.setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
        // agentd may add fields later (e.g. a future BenchmarkResult field)
        // — an unrecognized property should never break deserialization.
        agentdMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        MappingJackson2HttpMessageConverter agentdJsonConverter =
                new MappingJackson2HttpMessageConverter(agentdMapper);

        return builder.messageConverters(converters -> converters.add(0, agentdJsonConverter));
    }

    public HardwareProfileDto scanHardware() {
        return execute(() -> restClient.get()
                .uri("/hardware/scan")
                .retrieve()
                .body(HardwareProfileDto.class));
    }

    public HardwareProfileDto status() {
        return execute(() -> restClient.get()
                .uri("/status")
                .retrieve()
                .body(HardwareProfileDto.class));
    }

    public List<ModelCompatibilityDto> listModels() {
        return execute(() -> restClient.get()
                .uri("/models")
                .retrieve()
                .body(new ParameterizedTypeReference<List<ModelCompatibilityDto>>() {
                }));
    }

    public List<RunRecordDto> history(String modelId, int limit) {
        return execute(() -> restClient.get()
                .uri(uriBuilder -> {
                    var b = uriBuilder.path("/history").queryParam("limit", limit);
                    if (modelId != null) {
                        b = b.queryParam("model_id", modelId);
                    }
                    return b.build();
                })
                .retrieve()
                .body(new ParameterizedTypeReference<List<RunRecordDto>>() {
                }));
    }

    public RunResultDto run(String modelId, String prompt) {
        return execute(() -> restClient.post()
                .uri("/models/{modelId}/run", modelId)
                .body(Map.of("prompt", prompt))
                .retrieve()
                .body(RunResultDto.class));
    }

    public TuningSessionDto tune(String modelId, boolean dryRun) {
        return execute(() -> restClient.post()
                .uri("/models/{modelId}/tune", modelId)
                .body(Map.of("dry_run", dryRun))
                .retrieve()
                .body(TuningSessionDto.class));
    }

    public TunedConfigStatusDto autopilotStatus(String modelId) {
        return execute(() -> restClient.get()
                .uri("/autopilot/{modelId}/status", modelId)
                .retrieve()
                .body(TunedConfigStatusDto.class));
    }

    public void autopilotDisable(String modelId) {
        execute(() -> restClient.post()
                .uri("/autopilot/{modelId}/disable", modelId)
                .retrieve()
                .toBodilessEntity());
    }

    /**
     * Runs an agentd call, translating connection failures into
     * AgentdUnavailableException (agentd isn't running / unreachable) and
     * re-throwing agentd's own HTTP error responses (e.g. 503 "Ollama not
     * running", 404 "no tuned config yet") as-is so
     * GlobalExceptionHandler can map their status codes through to the
     * frontend rather than flattening everything into a generic 500.
     */
    private <T> T execute(Supplier<T> call) {
        try {
            return call.get();
        } catch (RestClientResponseException e) {
            throw e;
        } catch (RestClientException e) {
            throw new AgentdUnavailableException(
                    "Could not reach agentd — is it running? (" + e.getMessage() + ")", e
            );
        }
    }
}