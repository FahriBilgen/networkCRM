export interface User {
  id: string;
  email: string;
  fullName: string;
  sector: string;
  bio?: string;
  phone?: string;
  linkedinUrl?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName: string;
  sector: string;
  bio?: string;
  phone?: string;
  linkedinUrl?: string;
}

export interface PersonNode {
  id: string;
  type: 'PERSON' | 'GOAL' | 'VISION' | 'PROJECT' | 'COMPANY';
  name: string;
  sector: string;
  tags?: string[];
  notes?: string;
  relationshipStrength?: number;
  contactPhone?: string;
  contactEmail?: string;
  contactLinkedin?: string;
  linkedUserId?: string;
}

export interface CreatePersonRequest {
  type: 'PERSON';
  name: string;
  sector: string;
  tags?: string[];
  notes?: string;
  relationshipStrength?: number;
  phone?: string;
  email?: string;
  linkedin?: string;
}
