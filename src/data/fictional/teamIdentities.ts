export interface FictionalTeamIdentity {
  readonly city: string
  readonly nickname: string
  readonly abbreviation: string
  readonly colors: {
    readonly primary: string
    readonly secondary: string
    readonly accent: string
  }
}

/**
 * Curated complete identities built from invented places and nicknames. Keeping
 * each record intact prevents generation from accidentally recreating a real
 * professional basketball identity through arbitrary city/name recombination.
 */
export const FICTIONAL_TEAM_IDENTITIES: readonly FictionalTeamIdentity[] = [
  {
    city: 'Alderreach',
    nickname: 'Astrolabes',
    abbreviation: 'ARA',
    colors: { primary: '#26355d', secondary: '#f2b84b', accent: '#f5f1e8' },
  },
  {
    city: 'Brindleport',
    nickname: 'Beaconwrights',
    abbreviation: 'BRB',
    colors: { primary: '#315c52', secondary: '#e4a95b', accent: '#f2efe8' },
  },
  {
    city: 'Cindervale',
    nickname: 'Coursers',
    abbreviation: 'CVC',
    colors: { primary: '#6b3e2e', secondary: '#d98e4b', accent: '#f1d7a2' },
  },
  {
    city: 'Duskmere',
    nickname: 'Nightjars',
    abbreviation: 'DMN',
    colors: { primary: '#342a5e', secondary: '#8fb8de', accent: '#e8e3f2' },
  },
  {
    city: 'Emberlyn',
    nickname: 'Forgekeepers',
    abbreviation: 'EFK',
    colors: { primary: '#7a2e2e', secondary: '#e36f3d', accent: '#f3d6a3' },
  },
  {
    city: 'Foxglade',
    nickname: 'Kestrels',
    abbreviation: 'FGK',
    colors: { primary: '#365a3c', secondary: '#c7a94a', accent: '#f0ead2' },
  },
  {
    city: 'Glasswater',
    nickname: 'Navigators',
    abbreviation: 'GWN',
    colors: { primary: '#2f5964', secondary: '#78c4c8', accent: '#e7f3f1' },
  },
  {
    city: 'Highbarrow',
    nickname: 'Wardens',
    abbreviation: 'HBW',
    colors: { primary: '#4b4d2a', secondary: '#b8a24a', accent: '#f2e8c9' },
  },
  {
    city: 'Ironhollow',
    nickname: 'Firetails',
    abbreviation: 'IHF',
    colors: { primary: '#4a3330', secondary: '#d65a3a', accent: '#b7c9c4' },
  },
  {
    city: 'Juniper Reach',
    nickname: 'Wayfarers',
    abbreviation: 'JRW',
    colors: { primary: '#31506b', secondary: '#d09b45', accent: '#e9d7b2' },
  },
  {
    city: 'Lumen Bay',
    nickname: 'Tidemakers',
    abbreviation: 'LBT',
    colors: { primary: '#2b5361', secondary: '#4ca6a8', accent: '#f0c86a' },
  },
  {
    city: 'Mossbarrow',
    nickname: 'Skyweavers',
    abbreviation: 'MSW',
    colors: { primary: '#553b68', secondary: '#79a4c8', accent: '#f2d4a7' },
  },
]
