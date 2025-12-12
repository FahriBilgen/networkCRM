package com.fahribilgen.networkcrm.controller;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.FavoritePathRequest;
import com.fahribilgen.networkcrm.payload.FavoritePathResponse;
import com.fahribilgen.networkcrm.repository.UserRepository;
import com.fahribilgen.networkcrm.security.UserPrincipal;
import com.fahribilgen.networkcrm.service.FavoritePathService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/favorites")
public class FavoritePathController {

    private final FavoritePathService favoritePathService;
    private final UserRepository userRepository;

    public FavoritePathController(FavoritePathService favoritePathService, UserRepository userRepository) {
        this.favoritePathService = favoritePathService;
        this.userRepository = userRepository;
    }

    @GetMapping
    public ResponseEntity<List<FavoritePathResponse>> listFavorites(@AuthenticationPrincipal UserPrincipal currentUser) {
        return ResponseEntity.ok(favoritePathService.getFavorites(resolveUser(currentUser)));
    }

    @PostMapping
    public ResponseEntity<FavoritePathResponse> createFavorite(
            @AuthenticationPrincipal UserPrincipal currentUser,
            @Valid @RequestBody FavoritePathRequest request
    ) {
        return ResponseEntity.ok(favoritePathService.createFavorite(resolveUser(currentUser), request));
    }

    @DeleteMapping("/{favoriteId}")
    public ResponseEntity<Void> deleteFavorite(
            @AuthenticationPrincipal UserPrincipal currentUser,
            @PathVariable UUID favoriteId
    ) {
        favoritePathService.deleteFavorite(resolveUser(currentUser), favoriteId);
        return ResponseEntity.noContent().build();
    }

    private User resolveUser(UserPrincipal userPrincipal) {
        return userRepository.findById(userPrincipal.getId())
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
