package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.FavoritePathRequest;
import com.fahribilgen.networkcrm.payload.FavoritePathResponse;

import java.util.List;
import java.util.UUID;

public interface FavoritePathService {
    List<FavoritePathResponse> getFavorites(User user);

    FavoritePathResponse createFavorite(User user, FavoritePathRequest request);

    void deleteFavorite(User user, UUID favoriteId);
}
