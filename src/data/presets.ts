export interface PresetImage {
  label: string;
  category: string;
  url: string;
}

export const PRESET_IMAGES: PresetImage[] = [
  {
    label: 'PC Portable Dell Latitude',
    category: 'Portable',
    url: 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Lenovo ThinkPad Business',
    category: 'Portable',
    url: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'HP EliteBook Professionnel',
    category: 'Portable',
    url: 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Unité Centrale / PC Fixe Tour',
    category: 'Poste Fixe',
    url: 'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Serveur Rack Datacenter',
    category: 'Serveur',
    url: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Switch Réseau Cisco / Baie Brassage',
    category: 'Réseau',
    url: 'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Imprimante Multifonction Réseau',
    category: 'Imprimante',
    url: 'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Onduleur Haute Disponibilité',
    category: 'Onduleur',
    url: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=700&auto=format&fit=crop&q=80'
  },
  {
    label: 'Écran Professionnel Ergonomique',
    category: 'Écran',
    url: 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=700&auto=format&fit=crop&q=80'
  }
];
