package com.llmmax.webui;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * Verifies the full application context starts — every bean (including
 * AgentdClient, which does real work in its constructor: building the
 * SimpleClientHttpRequestFactory, configuring the snake_case ObjectMapper,
 * binding @Value properties from application.yml) wires together without
 * error. No network calls happen here — AgentdClient's constructor never
 * contacts agentd, it only builds the client.
 */
@SpringBootTest
class WebUiApplicationTests {

    @Test
    void contextLoads() {
    }
}
