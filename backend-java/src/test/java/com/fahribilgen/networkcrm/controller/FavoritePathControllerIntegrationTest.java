package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.FavoritePathRequest;
import com.fahribilgen.networkcrm.payload.FavoritePathResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.FavoritePathService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class FavoritePathControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private FavoritePathService favoritePathService;

    @MockBean
    private UserRepository userRepository;

    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .id(UUID.randomUUID())
                .email("favorites@test.com")
                .build();

        when(userRepository.findById(any(UUID.class))).thenReturn(Optional.of(testUser));
    }

    private void authenticate() {
        UserPrincipal principal = UserPrincipal.create(testUser);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities())
        );
    }

    @Test
    void shouldListFavorites() throws Exception {
        authenticate();
        FavoritePathResponse response = FavoritePathResponse.builder()
                .id(UUID.randomUUID())
                .goalId(UUID.randomUUID())
                .label("My Path")
                .nodeIds(List.of(UUID.randomUUID(), UUID.randomUUID()))
                .build();
        when(favoritePathService.getFavorites(any(User.class))).thenReturn(List.of(response));

        mockMvc.perform(get("/api/favorites"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].label").value("My Path"));
    }

    @Test
    void shouldCreateFavorite() throws Exception {
        authenticate();
        FavoritePathRequest request = new FavoritePathRequest();
        request.setGoalId(UUID.randomUUID());
        request.setLabel("Focus Path");
        request.setNodeIds(List.of(UUID.randomUUID()));

        FavoritePathResponse response = FavoritePathResponse.builder()
                .id(UUID.randomUUID())
                .goalId(request.getGoalId())
                .label(request.getLabel())
                .nodeIds(request.getNodeIds())
                .build();

        when(favoritePathService.createFavorite(any(User.class), any(FavoritePathRequest.class)))
                .thenReturn(response);

        mockMvc.perform(post("/api/favorites")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.label").value("Focus Path"));
    }

    @Test
    void shouldDeleteFavorite() throws Exception {
        authenticate();
        UUID favoriteId = UUID.randomUUID();
        doNothing().when(favoritePathService).deleteFavorite(any(User.class), eq(favoriteId));

        mockMvc.perform(delete("/api/favorites/" + favoriteId))
                .andExpect(status().isNoContent());
    }
}
