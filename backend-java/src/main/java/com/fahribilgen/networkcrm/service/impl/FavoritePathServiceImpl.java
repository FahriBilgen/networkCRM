package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.FavoritePath;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.FavoritePathRequest;
import com.fahribilgen.networkcrm.payload.FavoritePathResponse;
import com.fahribilgen.networkcrm.repository.FavoritePathRepository;
import com.fahribilgen.networkcrm.service.FavoritePathService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class FavoritePathServiceImpl implements FavoritePathService {

    private final FavoritePathRepository favoritePathRepository;

    @Override
    public List<FavoritePathResponse> getFavorites(User user) {
        return favoritePathRepository.findByUserId(user.getId()).stream()
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    @Override
    public FavoritePathResponse createFavorite(User user, FavoritePathRequest request) {
        if (request.getNodeIds() == null || request.getNodeIds().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Node list cannot be empty");
        }
        FavoritePath favoritePath = FavoritePath.builder()
                .user(user)
                .goalId(request.getGoalId())
                .label(request.getLabel())
                .nodeIds(request.getNodeIds())
                .build();
        FavoritePath saved = favoritePathRepository.save(favoritePath);
        return mapToResponse(saved);
    }

    @Override
    public void deleteFavorite(User user, UUID favoriteId) {
        FavoritePath favoritePath = favoritePathRepository.findByIdAndUserId(favoriteId, user.getId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Favorite path not found"));
        favoritePathRepository.delete(favoritePath);
    }

    private FavoritePathResponse mapToResponse(FavoritePath favoritePath) {
        return FavoritePathResponse.builder()
                .id(favoritePath.getId())
                .goalId(favoritePath.getGoalId())
                .label(favoritePath.getLabel())
                .nodeIds(favoritePath.getNodeIds())
                .createdAt(favoritePath.getCreatedAt())
                .build();
    }
}
